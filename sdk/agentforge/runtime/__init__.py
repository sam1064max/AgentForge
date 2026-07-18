"""Agent runtime context and execution result.

:class:`AgentContext` is injected into every agent instance. It exposes the
LLM client, memory, tool registry, prompt rendering, guardrails, and
observability handles. The context is backed by a :class:`RuntimeBackend`
abstraction so the same agent code runs locally (in-process backends) or in the
full platform (remote services).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentforge.gateway import LLMRequest, LLMResponse, ModelConfig
from agentforge.models import Message, ToolCall


@dataclass
class ExecutionResult:
    """The outcome of an agent execution."""

    output: str
    execution_id: str
    status: str = "completed"
    tool_calls: list[ToolCall] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
    cost_usd: float = 0.0
    latency_ms: int = 0
    trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "output": self.output,
            "execution_id": self.execution_id,
            "status": self.status,
            "tool_calls": [tc.model_dump() for tc in self.tool_calls],
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "trace_id": self.trace_id,
            "metadata": self.metadata,
            "error": self.error,
        }


class LLMClient:
    """Thin async facade over the Model Gateway used inside agents."""

    def __init__(self, backend: Any, *, agent_id: str | None = None,
                 tenant_id: str | None = None, execution_id: str | None = None,
                 trace_id: str | None = None) -> None:
        self._backend = backend
        self._agent_id = agent_id
        self._tenant_id = tenant_id
        self._execution_id = execution_id
        self._trace_id = trace_id

    async def generate(
        self,
        *,
        messages: list[Message] | list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[Any] | None = None,
        tool_choice: str = "auto",
        stream: bool = False,
    ) -> LLMResponse:
        norm: list[Message] = [
            m if isinstance(m, Message) else Message(**m) for m in messages
        ]
        request = LLMRequest(
            model=model or "default",
            messages=norm,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            stream=stream,
            agent_id=self._agent_id,
            tenant_id=self._tenant_id,
            execution_id=self._execution_id,
            trace_id=self._trace_id,
        )
        return await self._backend.complete(request)


class AgentContext:
    """The execution-time API surface handed to an agent instance."""

    def __init__(
        self,
        *,
        backend: Any,
        agent_id: str,
        execution_id: str,
        tenant_id: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.backend = backend
        self.agent_id = agent_id
        self.execution_id = execution_id
        self.tenant_id = tenant_id
        self.config = config or {}

        self.llm = LLMClient(
            backend,
            agent_id=agent_id,
            tenant_id=tenant_id,
            execution_id=execution_id,
            trace_id=getattr(backend, "trace_id", None),
        )
        self.memory = backend.get_memory(tenant_id=tenant_id, agent_id=agent_id)
        self.tools = backend.get_tool_registry()
        self.prompts = backend.get_prompt_registry()
        self.guardrails = backend.get_guardrail_registry()
        self.tracer = backend.get_tracer()

    async def escalate(self, *, to: str, reason: str, context: str | None = None) -> dict[str, Any]:
        """Request human-in-the-loop escalation."""
        return await self.backend.escalate(to=to, reason=reason, context=context)

    def model_config(self) -> ModelConfig | None:
        return getattr(self.backend, "model_config", None)
