# SPDX-License-Identifier: Apache-2.0
"""Core model configuration dataclasses for the AgentForge SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RoutingStrategy(str, Enum):
    """LLM routing strategy used by the model gateway."""

    COST_OPTIMIZED = "cost-optimized"
    LATENCY_OPTIMIZED = "latency-optimized"
    QUALITY_FIRST = "quality-first"
    BALANCED = "balanced"
    DEFAULT = "default"


class Capability(str, Enum):
    """Model capability tags recognised by the model registry."""

    CHAT = "chat"
    FUNCTION_CALLING = "function-calling"
    VISION = "vision"
    STRUCTURED_OUTPUT = "structured-output"
    EMBEDDING = "embedding"
    STREAMING = "streaming"
    REASONING = "reasoning"


@dataclass(slots=True)
class ModelConfig:
    """Declarative configuration for an agent's primary model and fallback chain.

    Examples
    --------
    >>> ModelConfig(
    ...     provider="openai",
    ...     model="gpt-4o",
    ...     fallback="anthropic/claude-sonnet-4-20250514",
    ...     routing=RoutingStrategy.COST_OPTIMIZED,
    ... )
    """

    provider: str = "openai"
    model: str = "gpt-4o"
    fallback: str | None = None
    routing: RoutingStrategy = RoutingStrategy.BALANCED
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    timeout_seconds: int = 120
    extra: dict[str, Any] = field(default_factory=dict)

    def logical_name(self) -> str:
        return f"{self.provider}/{self.model}"


@dataclass(slots=True)
class RetryConfig:
    """Retry policy for external calls (tools, models)."""

    max_attempts: int = 3
    backoff: str = "exponential"
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 30.0


@dataclass(slots=True)
class RateLimitConfig:
    """Rate limit configuration for a tool or model binding."""

    requests_per_minute: int = 60
    burst: int = 10


@dataclass(slots=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration for a dependency."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_requests: int = 3


@dataclass(slots=True)
class ToolBindingConfig:
    """Per-agent binding of a tool with permissions and limits."""

    name: str
    permissions: list[str] = field(default_factory=list)
    rate_limit: RateLimitConfig | None = None
    requires_approval: bool = False
    timeout_seconds: int = 30


@dataclass(slots=True)
class ModelRegistration:
    """A model registered with the model registry."""

    id: str
    provider: str
    name: str
    version: str = "latest"
    capabilities: list[Capability] = field(default_factory=list)
    context_window: int = 128_000
    max_output_tokens: int = 16_384
    input_price_per_1k: float = 0.0
    output_price_per_1k: float = 0.0
    status: str = "pending"
    data_residency: list[str] = field(default_factory=list)
    compliance: list[str] = field(default_factory=list)
