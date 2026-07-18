"""Agent execution engine.

The engine takes a registered agent, builds an :class:`AgentContext`, invokes
the declared handler, and — when the model emits tool calls — executes the tools
and feeds results back. It also enforces input/output guardrails and records a
trace. This is the local execution path used by the SDK's ``Agent.run()``.
"""

from __future__ import annotations

import asyncio
import inspect
import time
import uuid
from typing import Any

from agentforge.exceptions import ExecutionError
from agentforge.models import FunctionResult, Message, ToolCall
from agentforge.runtime import AgentContext, ExecutionResult
from agentforge.runtime.local import LocalBackend


async def execute_agent(
    definition: Any,
    *,
    message: str,
    backend: LocalBackend | None = None,
    tenant_id: str | None = None,
    session_id: str | None = None,
) -> ExecutionResult:
    """Run a registered agent on a single user message and return the result."""
    backend = backend or LocalBackend(tenant_id=tenant_id)
    execution_id = uuid.uuid4().hex
    agent_id = definition.name

    # Input guardrails
    if definition.guardrails:
        backend.enforce_input_guardrails(message, enabled=definition.guardrails)

    ctx = AgentContext(
        backend=backend,
        agent_id=agent_id,
        execution_id=execution_id,
        tenant_id=tenant_id,
        config={"session_id": session_id},
    )

    handlers = definition.handlers
    on_message = handlers.get("on_message")
    if on_message is None:
        raise ExecutionError(f"Agent '{agent_id}' has no @Agent.on_message handler")

    start = time.monotonic()
    trace_id = getattr(backend.get_tracer(), "trace_id", None)
    tool_calls: list[ToolCall] = []
    output = ""
    messages: list[Message] = []

    try:
        # Instantiate the agent and invoke the user-declared handler. The
        # handler owns the LLM/tool orchestration (it may call ctx.llm.generate,
        # ctx.backend.execute_tool, etc.). We capture tool calls the agent makes
        # through the backend by wrapping execute_tool. If the handler returns a
        # string, we treat it as the final output.
        instance = definition.instantiate(ctx)
        result = on_message(instance, message)
        if inspect.isawaitable(result):
            result = await result

        if isinstance(result, str):
            output = result
        elif isinstance(result, ExecutionResult):
            return result
        else:
            output = str(result)

        backend.enforce_output_guardrails(output, enabled=definition.guardrails or None)
    except Exception as exc:  # noqa: BLE001
        latency = int((time.monotonic() - start) * 1000)
        return ExecutionResult(
            output="", execution_id=execution_id, status="error",
            messages=messages, latency_ms=latency, trace_id=trace_id, error=str(exc),
        )

    latency = int((time.monotonic() - start) * 1000)
    return ExecutionResult(
        output=output, execution_id=execution_id, status="completed",
        tool_calls=tool_calls, messages=messages,
        latency_ms=latency, trace_id=trace_id,
    )


def _takes_cls(fn: Any) -> bool:
    sig = inspect.signature(fn)
    return len(sig.parameters) >= 1


def run_agent_sync(definition: Any, *, message: str, **kwargs: Any) -> ExecutionResult:
    """Synchronous wrapper for :func:`execute_agent`."""
    return asyncio.run(execute_agent(definition, message=message, **kwargs))
