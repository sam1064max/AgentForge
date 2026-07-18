# SPDX-License-Identifier: Apache-2.0
"""Core abstractions (interfaces) for the AgentForge platform.

These protocols define the contract that every concrete backend (local,
PostgreSQL, Qdrant, Kafka, Temporal, …) must satisfy. Implementations live in
their respective modules; the runtime depends only on these interfaces, which
keeps the platform backend-agnostic and trivially testable.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MemoryProvider(Protocol):
    """Storage and retrieval of agent memory across tiers."""

    async def store(self, *, scope: str, key: str, value: Any, **meta: Any) -> str: ...

    async def recall(self, *, scope: str, query: str, top_k: int = 5, **filters: Any) -> list[dict[str, Any]]: ...

    async def search(self, *, scope: str, vector: list[float], top_k: int = 5, **filters: Any) -> list[dict[str, Any]]: ...

    async def delete(self, memory_id: str) -> None: ...


@runtime_checkable
class VectorStore(Protocol):
    """Semantic vector index used by memory and knowledge."""

    async def upsert(self, *, collection: str, points: list[dict[str, Any]]) -> None: ...

    async def search(self, *, collection: str, vector: list[float], top_k: int = 10, score_threshold: float | None = None, **filters: Any) -> list[dict[str, Any]]: ...

    async def delete(self, *, collection: str, ids: list[str]) -> None: ...


@runtime_checkable
class KnowledgeStore(Protocol):
    """Document & chunk storage backing the RAG service."""

    async def add_document(self, *, source: str, title: str, chunks: list[dict[str, Any]]) -> str: ...

    async def search(self, *, query_vector: list[float], top_k: int = 10, **filters: Any) -> list[dict[str, Any]]: ...


@runtime_checkable
class ToolProvider(Protocol):
    """Executes registered tools on behalf of agents."""

    async def execute(self, *, tool: str, args: dict[str, Any], context: dict[str, Any]) -> Any: ...


@runtime_checkable
class ModelGateway(Protocol):
    """Unified LLM + embedding access across providers."""

    async def chat(self, request: Any) -> Any: ...

    async def embed(self, request: Any) -> Any: ...


@runtime_checkable
class PolicyEngine(Protocol):
    """Evaluates declarative policies against a context document."""

    async def evaluate(self, *, policy: str | None, action: str, context: dict[str, Any]) -> "PolicyDecision": ...


@runtime_checkable
class ObservabilitySink(Protocol):
    """Receives spans, metrics and structured log records."""

    def span(self, name: str, **attrs: Any) -> Any: ...

    def record(self, name: str, value: float, **attrs: Any) -> None: ...

    def log(self, level: str, message: str, **attrs: Any) -> None: ...


@runtime_checkable
class Guardrail(Protocol):
    """Input/output content guardrail."""

    name: str

    async def check(self, text: str, config: dict[str, Any]) -> "GuardrailResult": ...


@runtime_checkable
class EventBus(Protocol):
    """Event-driven backbone used across subsystems."""

    async def publish(self, topic: str, event: dict[str, Any]) -> None: ...

    async def subscribe(self, topic: str, handler: Any) -> None: ...
