"""Model Gateway configuration and request/response models.

The Model Gateway is the unified LLM access layer. These models define the
provider-neutral request/response contract used across the platform, plus the
routing strategies described in the architecture (cost / latency / quality /
balanced).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from agentforge.models import FinishReason, Message, ToolCall, Usage


class RoutingStrategy(str, Enum):
    """Strategy used by the LLM Router to select a model/provider."""

    COST = "cost"
    LATENCY = "latency"
    QUALITY = "quality"
    BALANCED = "balanced"
    CUSTOM = "custom"


class ModelConfig(BaseModel):
    """Configuration for the primary model and its fallback chain."""

    provider: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    stop: list[str] | None = None
    fallback: str | None = None  # "provider/model" or logical name
    routing: RoutingStrategy = RoutingStrategy.BALANCED
    timeout_seconds: int = 120

    @property
    def logical_name(self) -> str:
        return f"{self.provider}/{self.model}"


class LLMRequest(BaseModel):
    """Unified LLM request across all providers."""

    model: str
    messages: list[Message]
    routing_strategy: RoutingStrategy = RoutingStrategy.BALANCED
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    stop: list[str] | None = None
    tools: list[Any] | None = None
    tool_choice: str = "auto"
    response_format: dict[str, Any] | None = None
    stream: bool = False

    # AgentForge metadata
    agent_id: str | None = None
    execution_id: str | None = None
    tenant_id: str | None = None
    trace_id: str | None = None

    # Caching / budget
    cache_policy: str = "auto"  # auto | force | skip
    cache_ttl: int = 3600
    max_cost: float | None = None


class LLMResponse(BaseModel):
    """Unified LLM response."""

    message: Message
    tool_calls: list[ToolCall] = Field(default_factory=list)
    model: str
    provider: str
    usage: Usage = Field(default_factory=Usage)
    finish_reason: FinishReason = FinishReason.STOP
    cached: bool = False
    latency_ms: int = 0
    trace_id: str | None = None
    fallback_used: bool = False


from agentforge.gateway.providers import (  # noqa: E402
    AnthropicProvider,
    BaseProvider,
    MockProvider,
    OpenAIProvider,
    ProviderRegistry,
    provider_registry,
)

__all__ = [
    "ModelConfig",
    "RoutingStrategy",
    "LLMRequest",
    "LLMResponse",
    "BaseProvider",
    "MockProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "ProviderRegistry",
    "provider_registry",
]
