"""AgentForge exception hierarchy.

All errors raised by the AgentForge SDK derive from :class:`AgentForgeError`
so callers can catch platform errors uniformly.
"""

from __future__ import annotations


class AgentForgeError(Exception):
    """Base class for all AgentForge errors."""

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        if self.cause is not None:
            return f"{self.message} (caused by {type(self.cause).__name__}: {self.cause})"
        return self.message


class ConfigurationError(AgentForgeError):
    """Raised when the platform or agent is misconfigured."""


class ValidationError(AgentForgeError):
    """Raised when a manifest, prompt, or input fails validation."""


class AgentNotFoundError(AgentForgeError):
    """Raised when a referenced agent cannot be resolved."""


class ExecutionError(AgentForgeError):
    """Raised when an agent execution fails unrecoverably."""


class ToolError(AgentForgeError):
    """Raised when a tool execution fails."""


class ProviderError(AgentForgeError):
    """Raised when an upstream LLM provider fails."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        status_code: int | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.provider = provider
        self.status_code = status_code


class GuardrailError(AgentForgeError):
    """Raised when a guardrail blocks content."""

    def __init__(
        self,
        message: str,
        *,
        guardrail: str | None = None,
        severity: str = "critical",
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.guardrail = guardrail
        self.severity = severity


class PolicyDeniedError(AgentForgeError):
    """Raised when a policy engine denies an action."""

    def __init__(
        self,
        message: str,
        *,
        policy: str | None = None,
        reasons: list[str] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.policy = policy
        self.reasons = reasons or []


class BudgetExceededError(AgentForgeError):
    """Raised when a cost budget is exceeded."""

    def __init__(
        self,
        message: str,
        *,
        limit: float | None = None,
        spent: float | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.limit = limit
        self.spent = spent


class CircuitOpenError(AgentForgeError):
    """Raised when a circuit breaker is open and rejects a call."""

    def __init__(
        self,
        message: str,
        *,
        resource: str | None = None,
        reset_timeout: float | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.resource = resource
        self.reset_timeout = reset_timeout
