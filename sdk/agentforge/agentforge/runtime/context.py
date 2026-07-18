# SPDX-License-Identifier: Apache-2.0
"""Agent execution context and result types.

The :class:`AgentContext` is the single object passed to every agent hook. It
provides type-safe access to memory, tools, the model gateway, prompts,
guardrails, observability and human-in-the-loop escalation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from agentforge.interfaces import MemoryProvider, ModelGateway, ObservabilitySink, ToolProvider
from agentforge.models.llm import LLMRequest, LLMResponse, Message
from agentforge.types import ExecutionResult


@dataclass
class AgentContext:
    """Mutable execution context for a single agent run.

    Instances are constructed by the runtime and injected into the agent class.
    They are *not* meant to be created by application code.
    """

    agent_id: str
    tenant_id: str
    execution_id: str = field(default_factory=lambda: f"exec-{uuid4().hex[:12]}")
    session_id: str | None = None
    user_id: str | None = None
    trigger_type: str = "api"

    # Injected collaborators (set by the runtime)
    llm: ModelGateway | None = None
    memory: MemoryProvider | None = None
    tools: ToolProvider | None = None
    prompts: Any | None = None
    guardrails: Any | None = None
    observability: ObservabilitySink | None = None
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    async def generate(
        self,
        *,
        messages: list[Message] | list[dict[str, Any]],
        model: str | None = None,
        tools: list[Any] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Convenience wrapper around the model gateway ``chat`` call."""
        if self.llm is None:
            raise RuntimeError("Model gateway not configured for this context")
        if messages and isinstance(messages[0], dict):
            messages = [Message(**m) for m in messages]  # type: ignore[arg-type]
        if tools:
            from agentforge.models.llm import ToolDefinition

            tools = [
                ToolDefinition(**t) if isinstance(t, dict) else t  # type: ignore[arg-type]
                for t in tools
            ]
        request = LLMRequest(
            messages=list(messages),  # type: ignore[arg-type]
            model=model or self.config.get("model", "openai/gpt-4o"),
            tools=tools,
            temperature=temperature if temperature is not None else self.config.get("temperature", 0.7),
            max_tokens=max_tokens or self.config.get("max_tokens", 4096),
            agent_id=self.agent_id,
            execution_id=self.execution_id,
            tenant_id=self.tenant_id,
            **kwargs,
        )
        return await self.llm.chat(request)

    async def escalate(self, *, to: str, reason: str, context: str | None = None) -> dict[str, Any]:
        """Escalate the current execution to a human reviewer."""
        payload = {
            "execution_id": self.execution_id,
            "agent_id": self.agent_id,
            "assignee": to,
            "reason": reason,
            "context": context or "",
        }
        if self.observability is not None:
            self.observability.log("info", "escalation triggered", **payload)
        self.metadata.setdefault("escalations", []).append(payload)
        return payload

    def to_result(self, *, output: str, **kwargs: Any) -> ExecutionResult:
        return ExecutionResult(
            execution_id=self.execution_id,
            output=output,
            **kwargs,
        )
