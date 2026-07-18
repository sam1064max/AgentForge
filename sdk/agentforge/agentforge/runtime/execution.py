# SPDX-License-Identifier: Apache-2.0
"""Agent runtime: execution engine and tool executor.

The :class:`AgentRuntime` loads an agent spec, builds an :class:`AgentContext`,
enforces input guardrails, runs the agent's message handler, executes any tool
calls requested by the model (with permission/rate-limit/circuit-breaker
wrapping), applies output guardrails, and records the full observability trace.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from agentforge.agent import AgentBase, AgentSpec
from agentforge.errors import GuardrailBlockedError, ToolError
from agentforge.guardrail import GuardrailRegistry
from agentforge.interfaces import MemoryProvider, ModelGateway, ObservabilitySink, ToolProvider
from agentforge.models.llm import LLMResponse, Message, ToolCall
from agentforge.models.config import CircuitBreakerConfig, RateLimitConfig, RetryConfig
from agentforge.observability.local import LocalObservability
from agentforge.runtime.context import AgentContext
from agentforge.tool import ToolSpec, get_tool_spec, is_tool
from agentforge.types import ExecutionResult, ToolResult


@dataclass(slots=True)
class ToolExecutorState:
    """Circuit breaker + rate-limit state for a single tool."""

    failures: int = 0
    open_until: float = 0.0
    tokens: float = 0.0  # simple token-bucket counter (seconds)


class ToolExecutor(ToolProvider):
    """Executes registered tool functions with resilience wrappers."""

    def __init__(self, *, rate_limit_granularity: str = "global") -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._state: dict[str, ToolExecutorState] = {}

    def register(self, fn: Callable[..., Any]) -> None:
        spec = get_tool_spec(fn)
        self._tools[spec.name] = spec

    def register_module(self, module: Any) -> None:
        for attr in vars(module).values():
            if callable(attr) and is_tool(attr):
                self.register(attr)

    def _state_for(self, name: str) -> ToolExecutorState:
        return self._state.setdefault(name, ToolExecutorState())

    async def execute(self, *, tool: str, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        spec = self._tools.get(tool)
        if spec is None:
            raise ToolError(f"Unknown tool: {tool}")
        st = self._state_for(tool)
        now = time.time()
        if st.open_until > now:
            raise ToolError(f"Circuit open for tool {tool}")
        start = time.perf_counter()
        try:
            result = await self._invoke(spec, args)
            st.failures = 0
            return ToolResult(success=True, output=result, latency_ms=int((time.perf_counter() - start) * 1000))
        except Exception as e:  # noqa: BLE001
            st.failures += 1
            cb = spec.circuit_breaker
            if cb is not None and st.failures >= cb.failure_threshold:
                st.open_until = now + cb.recovery_timeout
            return ToolResult(success=False, error=str(e), latency_ms=int((time.perf_counter() - start) * 1000))

    async def _invoke(self, spec: ToolSpec, args: dict[str, Any]) -> Any:
        policy: RetryConfig = spec.retry_policy
        attempts = max(1, policy.max_attempts)
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                if inspect.iscoroutinefunction(spec.fn):
                    return await spec.fn(**args)
                return spec.fn(**args)
            except Exception as e:  # noqa: BLE001
                last_exc = e
                if attempt < attempts - 1:
                    delay = min(policy.max_delay_seconds, policy.base_delay_seconds * (2**attempt))
                    await asyncio.sleep(delay)
        assert last_exc is not None
        raise last_exc


class AgentRuntime:
    """Executes an agent spec against a fully wired context."""

    def __init__(
        self,
        gateway: ModelGateway,
        tools: ToolExecutor,
        memory: MemoryProvider | None = None,
        guardrails: GuardrailRegistry | None = None,
        observability: ObservabilitySink | None = None,
        prompts: Any | None = None,
    ) -> None:
        self.gateway = gateway
        self.tools = tools
        self.memory = memory
        self.guardrails = guardrails or GuardrailRegistry()
        self.observability = observability or LocalObservability()
        self.prompts = prompts

    async def run(
        self,
        spec: AgentSpec,
        message: str,
        *,
        tenant_id: str = "default",
        user_id: str | None = None,
        session_id: str | None = None,
        tools_override: dict[str, Callable[..., Any]] | None = None,
        max_steps: int = 8,
    ) -> ExecutionResult:
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        ctx = AgentContext(
            agent_id=spec.name,
            tenant_id=tenant_id,
            execution_id=execution_id,
            session_id=session_id,
            user_id=user_id,
            llm=self.gateway,
            memory=self.memory,
            tools=self.tools,
            prompts=self.prompts,
            guardrails=self.guardrails,
            observability=self.observability,
            config={"model": spec.model.logical_name(), "temperature": spec.model.temperature, "max_tokens": spec.model.max_tokens},
        )
        if tools_override:
            for name, fn in tools_override.items():
                self.tools.register(fn)

        # Seed conversation history (used when agents call ctx.generate() with no messages).
        ctx.metadata["history"] = [Message(role="user", content=message)]

        with self.observability.span("agent.execute", agentforge_agent_id=spec.name, agentforge_execution_id=execution_id, agentforge_tenant_id=tenant_id) as root:  # noqa: E501
            # Input guardrails
            if spec.guardrails:
                with self.observability.span("guardrail.input_check"):
                    res = await self.guardrails.run_input(message, spec.guardrails)
                    if not res.passed:
                        return ctx.to_result(output="", status="blocked", metadata={"error": "blocked by input guardrail"})

            agent = self._instantiate(spec, ctx)
            hook = spec.hooks.get("on_message")
            output = message
            tool_calls: list[tuple[str, dict[str, Any]]] = []
            llm_calls = 0
            tokens = 0
            cost = 0.0

            for step in range(max_steps):
                with self.observability.span("agent.step", step=step):
                    if hook is None:
                        break
                    method = getattr(agent, hook.__name__, None)
                    if method is None:
                        method = hook
                    if asyncio.iscoroutinefunction(method):
                        await method(output)
                    else:
                        method(output)

                    last: LLMResponse | None = ctx.metadata.get("last_llm_response")
                    if last is None:
                        # Handler did not call ctx.generate(); treat its return as the answer.
                        output = ctx.metadata.get("final_answer", output)
                        break

                    llm_calls += 1
                    tokens += last.total_tokens
                    cost += last.cost
                    self.observability.record("agentforge.llm.tokens_total", last.total_tokens)
                    self.observability.record("agentforge.llm.cost_usd", last.cost)
                    ctx.metadata.setdefault("history", []).append(last.message)

                    # Execute any tool calls the model requested, then loop.
                    if last.tool_calls:
                        for tc in last.tool_calls:
                            with self.observability.span("tool.execute", agentforge_tool_name=tc.name):
                                res = await self.tools.execute(
                                    tool=tc.name, args=tc.arguments,
                                    context={"agent_id": spec.name, "tenant_id": tenant_id},
                                )
                                tool_calls.append((tc.name, tc.arguments))
                                ctx.metadata.setdefault("tool_results", []).append({tc.name: res.output})
                                if not res.success:
                                    self.observability.log("error", "tool failed", tool=tc.name, error=res.error)
                        # Append tool results to the conversation and continue the loop
                        # so the model can produce a final natural-language answer.
                        ctx.metadata.pop("last_llm_response", None)
                        ctx.metadata.setdefault("pending_tool_results", []).append((last, tool_calls))
                        continue

                    output = last.message.content or ctx.metadata.get("final_answer", output)
                    break

            # Output guardrails
            if spec.guardrails:
                with self.observability.span("guardrail.output_check"):
                    res = await self.guardrails.run_output(output, spec.guardrails)
                    if not res.passed:
                        return ctx.to_result(output="", status="blocked", metadata={"error": "blocked by output guardrail"})
                    if res.modified_text is not None:
                        output = res.modified_text

        return ctx.to_result(
            output=output,
            tool_calls=tool_calls,
            llm_calls=llm_calls,
            total_tokens=tokens,
            cost=cost,
            latency_ms=int(root.duration_ms),
            trace_id=root.trace_id,
        )

    def _instantiate(self, spec: AgentSpec, ctx: AgentContext) -> AgentBase:
        if spec.cls is None:
            raise RuntimeError(f"Agent {spec.name} has no bound class")
        return spec.cls(ctx)
