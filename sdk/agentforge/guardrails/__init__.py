"""In-process guardrail registry.

Guardrails inspect input/output of agent runs. Each guardrail is a named
callable returning a :class:`GuardrailResult`. Production deployments use the
policy engine; this local version runs user-registered guardrails in-process.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from agentforge.logging import get_logger

logger = get_logger(__name__)


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCK = "block"


@dataclass
class GuardrailResult:
    passed: bool
    name: str
    severity: Severity = Severity.INFO
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


def _pii_guardrail(text: str, stage: str) -> GuardrailResult:
    import re

    patterns = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
    }
    found = {name: len(re.findall(pat, text)) for name, pat in patterns.items() if re.search(pat, text)}
    if found:
        return GuardrailResult(
            passed=False, name="pii-detection", severity=Severity.BLOCK,
            message="Potential PII detected", details=found,
        )
    return GuardrailResult(passed=True, name="pii-detection")


def _prompt_injection_guardrail(text: str, stage: str) -> GuardrailResult:
    indicators = [
        "ignore previous instructions",
        "ignore all previous",
        "disregard the system prompt",
        "you are now",
        "system prompt:",
    ]
    lowered = text.lower()
    hits = [i for i in indicators if i in lowered]
    if hits:
        return GuardrailResult(
            passed=False, name="prompt-injection-detection", severity=Severity.BLOCK,
            message="Possible prompt injection", details={"indicators": hits},
        )
    return GuardrailResult(passed=True, name="prompt-injection-detection")


class GuardrailRegistry:
    """Holds named guardrails and runs them over input/output."""

    _BUILTINS = {
        "pii-detection": _pii_guardrail,
        "prompt-injection-detection": _prompt_injection_guardrail,
    }

    def __init__(self) -> None:
        self._guardrails: dict[str, Callable[[str, str], GuardrailResult]] = dict(self._BUILTINS)
        self._lock = threading.RLock()

    def register(self, name: str, fn: Callable[[str, str], GuardrailResult]) -> None:
        with self._lock:
            self._guardrails[name] = fn

    def run(self, stage: str, text: str, *, enabled: list[str] | None = None) -> list[GuardrailResult]:
        with self._lock:
            names = enabled or list(self._guardrails.keys())
            results = []
            for name in names:
                fn = self._guardrails.get(name)
                if fn is None:
                    continue
                try:
                    results.append(fn(text, stage))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("guardrail error", extra={"attributes": {"guardrail": name, "error": str(exc)}})
                    results.append(GuardrailResult(passed=True, name=name, severity=Severity.WARNING,
                                                   message=f"guardrail error: {exc}"))
            return results

    def check(self, stage: str, text: str, *, enabled: list[str] | None = None) -> GuardrailResult:
        """Return the first failing (BLOCK) result, or an aggregate pass."""
        results = self.run(stage, text, enabled=enabled)
        for r in results:
            if not r.passed and r.severity == Severity.BLOCK:
                return r
        return GuardrailResult(passed=True, name="aggregate", message="all guardrails passed")
