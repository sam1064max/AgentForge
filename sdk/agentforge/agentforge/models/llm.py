# SPDX-License-Identifier: Apache-2.0
"""LLM request/response models for the model gateway abstraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agentforge.models.config import RoutingStrategy


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(slots=True)
class Message:
    """A single chat message."""

    role: str
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass(slots=True)
class ToolDefinition:
    """Schema for a tool the model may call."""

    name: str
    description: str
    parameters: dict[str, Any]
    required: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ToolCall:
    """A tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class LLMRequest:
    """Unified LLM request across all providers."""

    messages: list[Message]
    model: str = "openai/gpt-4o"
    routing_strategy: str = "default"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    stop: list[str] | None = None
    tools: list[ToolDefinition] | None = None
    tool_choice: str = "auto"
    response_format: dict[str, Any] | None = None
    stream: bool = False
    agent_id: str | None = None
    execution_id: str | None = None
    tenant_id: str | None = None
    cache_policy: str = "auto"
    cache_ttl: int = 3600
    max_cost: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMResponse:
    """Unified LLM response."""

    message: Message
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    provider: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    cached: bool = False
    fallback_used: bool = False
    trace_id: str = ""
    span_id: str = ""
    finish_reason: str = "stop"

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": {"role": self.message.role, "content": self.message.content},
            "tool_calls": [tc.__dict__ for tc in self.tool_calls],
            "model": self.model,
            "provider": self.provider,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
            "cached": self.cached,
            "finish_reason": self.finish_reason,
        }


@dataclass(slots=True)
class EmbeddingRequest:
    """Request to generate embeddings for one or more texts."""

    texts: list[str]
    model: str = "openai/text-embedding-3-large"
    tenant_id: str | None = None


@dataclass(slots=True)
class EmbeddingResponse:
    """Response containing generated embeddings."""

    vectors: list[list[float]]
    model: str = ""
    dimensions: int = 0
    cost: float = 0.0

    @property
    def vector(self) -> list[float]:
        """Convenience accessor for single-text requests."""
        if len(self.vectors) != 1:
            raise ValueError("vector accessor requires a single-text request")
        return self.vectors[0]
