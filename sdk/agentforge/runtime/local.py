"""In-process runtime backend.

:class:`LocalBackend` is the default backend for the SDK. It wires together
local memory, prompt registry, guardrail registry, tracer, and the provider
registry so agents run without any external infrastructure. Production
deployments provide a remote backend (e.g. via the Agent Runtime service).
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from agentforge.exceptions import GuardrailError
from agentforge.gateway import LLMRequest, LLMResponse, provider_registry
from agentforge.guardrails import GuardrailRegistry
from agentforge.logging import get_logger, new_trace_id
from agentforge.memory import ConversationMemory, KVStore, SemanticMemory
from agentforge.models import FunctionResult, Message, ToolCall
from agentforge.prompts import PromptRegistry
from agentforge.registry import registry
from agentforge.runtime.backend import RuntimeBackend

logger = get_logger(__name__)


class LocalBackend(RuntimeBackend):
    """Local, in-process implementation of :class:`RuntimeBackend`."""

    def __init__(
        self,
        *,
        model_config: Any = None,
        memory: Any = None,
        prompts: PromptRegistry | None = None,
        guardrails: GuardrailRegistry | None = None,
        tracer: Any = None,
        enable_otel: bool = False,
        tenant_id: str | None = None,
    ) -> None:
        self.model_config = model_config
        self.tenant_id = tenant_id
        self._memory = memory or ConversationMemory()
        self._prompts = prompts or PromptRegistry()
        self._guardrails = guardrails or GuardrailRegistry()
        self._tracer = tracer or _TracerProxy(enable_otel=enable_otel)
        self._kv = KVStore(namespace="local")
        self._semantic = SemanticMemory()

    # ── LLM ─────────────────────────────────────────────────
    async def complete(self, request: LLMRequest) -> LLMResponse:
        provider = provider_registry.get(request.model)
        # Apply model config overrides if present.
        if self.model_config is not None:
            request = request.model_copy(update={
                "temperature": self.model_config.temperature,
                "max_tokens": self.model_config.max_tokens,
                "top_p": self.model_config.top_p,
            })
        span = self._tracer.start_span("llm.complete", attributes={"model": request.model})
        try:
            response = await provider.complete(request)
            self._tracer.record_event(span, "llm.response", {
                "provider": response.provider,
                "finish_reason": response.finish_reason.value,
                "cost_usd": response.usage.cost_usd,
            })
            return response
        finally:
            self._tracer.end_span(span)

    # ── Memory ──────────────────────────────────────────────
    def get_memory(self, *, tenant_id: str | None, agent_id: str | None) -> Any:
        # ConversationMemory is session-scoped; for simplicity return the shared
        # local conversation store keyed by agent_id.
        return self._memory

    def get_semantic_memory(self) -> SemanticMemory:
        return self._semantic

    # ── Registries ──────────────────────────────────────────
    def get_tool_registry(self) -> Any:
        return registry

    def get_prompt_registry(self) -> PromptRegistry:
        return self._prompts

    def get_guardrail_registry(self) -> GuardrailRegistry:
        return self._guardrails

    def get_tracer(self) -> Any:
        return self._tracer

    # ── Guardrails enforcement ──────────────────────────────
    def enforce_input_guardrails(self, text: str, *, enabled: list[str] | None = None) -> None:
        result = self._guardrails.check("input", text, enabled=enabled)
        if not result.passed and result.severity.value == "block":
            raise GuardrailError(result.message, guardrail=result.name, details=result.details)

    def enforce_output_guardrails(self, text: str, *, enabled: list[str] | None = None) -> None:
        result = self._guardrails.check("output", text, enabled=enabled)
        if not result.passed and result.severity.value == "block":
            raise GuardrailError(result.message, guardrail=result.name, details=result.details)

    # ── Tool execution ──────────────────────────────────────
    async def execute_tool(self, call: ToolCall) -> FunctionResult:
        definition = registry.get_tool(call.function.name)
        args = _parse_arguments(call.function.arguments)
        span = self._tracer.start_span(f"tool.{definition.name}", attributes={"tool": definition.name})
        try:
            raw = await definition.invoke(**args)
            content = raw if isinstance(raw, str) else json.dumps(raw, default=str)
            return FunctionResult(tool_call_id=call.id, name=definition.name, content=content)
        except Exception as exc:  # noqa: BLE001
            return FunctionResult(tool_call_id=call.id, name=definition.name,
                                  content=f"error: {exc}", is_error=True)
        finally:
            self._tracer.end_span(span)

    # ── Escalation / events ────────────────────────────────
    async def escalate(self, *, to: str, reason: str, context: str | None) -> dict[str, Any]:
        ticket_id = uuid.uuid4().hex[:12]
        logger.info("escalation created", extra={"attributes": {"to": to, "ticket": ticket_id}})
        return {"ticket_id": ticket_id, "to": to, "reason": reason, "status": "open"}

    async def emit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        logger.info("event", extra={"attributes": {"event": event_type, "payload": payload}})


def _parse_arguments(arguments: str) -> dict[str, Any]:
    if not arguments:
        return {}
    try:
        return json.loads(arguments)
    except Exception:
        return {}


class _TracerProxy:
    """Lazy tracer holder so the backend exposes a stable tracer handle."""

    def __init__(self, *, enable_otel: bool = False, trace_id: str | None = None) -> None:
        from agentforge.observability.tracer import Tracer

        self._tracer = Tracer(enable_otel=enable_otel, trace_id=trace_id or new_trace_id())

    def __getattr__(self, item: str) -> Any:
        return getattr(self._tracer, item)
