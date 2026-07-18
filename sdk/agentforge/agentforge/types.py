# SPDX-License-Identifier: Apache-2.0
"""Shared result dataclasses used across the SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(slots=True)
class PolicyDecision:
    """Result of a policy evaluation."""

    decision: Decision
    reasons: list[str] = field(default_factory=list)
    policy_id: str | None = None
    cached: bool = False

    @property
    def allowed(self) -> bool:
        return self.decision == Decision.ALLOW


@dataclass(slots=True)
class GuardrailFinding:
    """A single finding produced by a guardrail."""

    type: str
    score: float = 1.0
    detail: str = ""
    span: tuple[int, int] | None = None


@dataclass(slots=True)
class GuardrailResult:
    """Result of running a guardrail over a piece of text."""

    passed: bool
    modified_text: str | None = None
    findings: list[GuardrailFinding] = field(default_factory=list)
    score: float = 1.0


@dataclass(slots=True)
class ToolResult:
    """Normalised result of a tool execution."""

    success: bool
    output: Any = None
    error: str | None = None
    latency_ms: int = 0
    cost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionResult:
    """Outcome of running an agent execution."""

    execution_id: str
    output: str
    status: str = "completed"
    tool_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    llm_calls: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    trace_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievedChunk:
    """A chunk returned by the RAG retrieval pipeline."""

    id: str
    content: str
    score: float = 0.0
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConstructedContext:
    """Context assembled for LLM generation from retrieved chunks."""

    text: str
    chunks: list[RetrievedChunk]
    token_count: int = 0
    sources: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BusinessKPI:
    """A tracked business KPI value."""

    name: str
    value: float
    attribution_model: str = "direct"
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
