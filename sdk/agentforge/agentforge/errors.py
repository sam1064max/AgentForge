# SPDX-License-Identifier: Apache-2.0
"""AgentForge exception hierarchy.

All AgentForge-specific errors derive from :class:`AgentForgeError` so that callers
can catch the whole family with a single ``except`` clause while still being able
to distinguish fine-grained failure modes.
"""

from __future__ import annotations

from typing import Any


class AgentForgeError(Exception):
    """Base class for every AgentForge error."""

    status_code: int = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(AgentForgeError):
    """Raised when the platform or an agent is mis-configured."""

    status_code = 400


class ValidationError(AgentForgeError):
    """Raised when a manifest, prompt, or tool definition fails validation."""

    status_code = 422


class PolicyDeniedError(AgentForgeError):
    """Raised when a policy engine denies an action."""

    status_code = 403

    def __init__(
        self,
        message: str,
        *,
        policy_id: str | None = None,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.policy_id = policy_id
        self.reason = reason


class GuardrailBlockedError(AgentForgeError):
    """Raised when a guardrail blocks input or output content."""

    status_code = 400

    def __init__(
        self,
        message: str,
        *,
        guardrail: str | None = None,
        findings: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.guardrail = guardrail
        self.findings = findings or []


class BudgetExceededError(AgentForgeError):
    """Raised when an entity exceeds its configured spend budget."""

    status_code = 429

    def __init__(
        self,
        message: str,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        budget_limit: float | None = None,
        current_spend: float | None = None,
    ) -> None:
        super().__init__(message)
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.budget_limit = budget_limit
        self.current_spend = current_spend


class RateLimitError(AgentForgeError):
    """Raised when a rate limit (tool, model, or tenant) is exceeded."""

    status_code = 429

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class CircuitOpenError(AgentForgeError):
    """Raised when a circuit breaker is open for a dependency."""

    status_code = 503

    def __init__(self, target: str, reset_timeout: float) -> None:
        super().__init__(f"Circuit breaker open for {target}; retry after {reset_timeout}s")
        self.target = target
        self.reset_timeout = reset_timeout


class ToolError(AgentForgeError):
    """Raised when a tool execution fails irrecoverably."""

    status_code = 502


class ModelGatewayError(AgentForgeError):
    """Raised when the model gateway cannot fulfil a request."""

    status_code = 502


class MemoryError_(AgentForgeError):
    """Raised on memory store/recall failures."""

    status_code = 500


class KnowledgeError(AgentForgeError):
    """Raised on knowledge/RAG retrieval failures."""

    status_code = 500


class OrchestrationError(AgentForgeError):
    """Raised when multi-agent orchestration fails."""

    status_code = 500


class ApprovalRequiredError(AgentForgeError):
    """Raised when an action requires (and lacks) human approval."""

    status_code = 409

    def __init__(self, message: str, *, approval_id: str | None = None) -> None:
        super().__init__(message)
        self.approval_id = approval_id


class CheckpointError(AgentForgeError):
    """Raised when checkpointing or resuming an execution fails."""

    status_code = 500
