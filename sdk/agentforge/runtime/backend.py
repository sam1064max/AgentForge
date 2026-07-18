"""Runtime backend abstraction.

A :class:`RuntimeBackend` provides the concrete implementations behind
:class:`~agentforge.runtime.AgentContext`. The SDK ships a
:class:`~agentforge.runtime.local.LocalBackend` that runs everything in-process
(no external infrastructure). Production deployments provide a remote backend
that talks to the AgentForge microservices.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agentforge.gateway import LLMRequest, LLMResponse
from agentforge.models import Message


class RuntimeBackend(ABC):
    """Contract for execution backends."""

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    def get_memory(self, *, tenant_id: str | None, agent_id: str | None) -> Any: ...

    @abstractmethod
    def get_tool_registry(self) -> Any: ...

    @abstractmethod
    def get_prompt_registry(self) -> Any: ...

    @abstractmethod
    def get_guardrail_registry(self) -> Any: ...

    @abstractmethod
    def get_tracer(self) -> Any: ...

    @abstractmethod
    async def escalate(self, *, to: str, reason: str, context: str | None) -> dict[str, Any]: ...

    @abstractmethod
    async def emit_event(self, event_type: str, payload: dict[str, Any]) -> None: ...
