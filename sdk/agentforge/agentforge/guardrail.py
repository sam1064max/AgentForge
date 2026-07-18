# SPDX-License-Identifier: Apache-2.0
"""Guardrails: input/output safety checks.

Ships a :class:`GuardrailRegistry` with built-in guardrails matching the
architecture (PII detection, prompt-injection, topic-restriction, jailbreak,
toxicity, format-validation, …). Offline implementations use deterministic
heuristics so the SDK works without external services; production deployments
register Presidio/LLM-backed guardrails behind the same interface.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar

from agentforge.errors import GuardrailBlockedError
from agentforge.interfaces import Guardrail
from agentforge.types import GuardrailFinding, GuardrailResult


_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

_INJECTION_PATTERNS = [
    r"ignore (all|previous|above|prior) (instructions|prompts)",
    r"disregard (your|the) (instructions|system message|prompt)",
    r"you are now",
    r"system prompt",
    r"reveal your (instructions|prompt)",
    r"jailbreak",
    r"DAN mode",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

_TOXIC_WORDS = ["idiot", "stupid", "hate", "kill", "worthless"]
_BIAS_TERMS = ["all (men|women) are", "typically (lazy|smart)", "you people"]


class BaseGuardrail(Guardrail):
    name = "base"

    async def check(self, text: str, config: dict[str, Any]) -> GuardrailResult:
        return GuardrailResult(passed=True)


class PIIDetectionGuard(BaseGuardrail):
    name = "pii-detection"

    _PATTERNS = {
        "EMAIL_ADDRESS": _EMAIL,
        "PHONE_NUMBER": _PHONE,
        "SSN": _SSN,
        "CREDIT_CARD": _CREDIT_CARD,
        "IP_ADDRESS": _IP,
    }

    async def check(self, text: str, config: dict[str, Any]) -> GuardrailResult:
        findings: list[GuardrailFinding] = []
        for pii_type, pattern in self._PATTERNS.items():
            for m in pattern.finditer(text):
                findings.append(GuardrailFinding(type=pii_type, span=(m.start(), m.end()), detail=m.group(0)))
        if not findings:
            return GuardrailResult(passed=True)
        if config.get("action") == "redact":
            redacted = text
            for f in findings:
                redacted = redacted.replace(f.detail, f"[{f.type}]")
            return GuardrailResult(passed=True, modified_text=redacted, findings=findings, score=0.5)
        return GuardrailResult(passed=False, findings=findings, score=0.1)


class PromptInjectionGuard(BaseGuardrail):
    name = "prompt-injection"

    async def check(self, text: str, config: dict[str, Any]) -> GuardrailResult:
        m = _INJECTION_RE.search(text)
        if m:
            return GuardrailResult(
                passed=False,
                findings=[GuardrailFinding(type="prompt-injection", detail=m.group(0))],
                score=0.1,
            )
        return GuardrailResult(passed=True)


class TopicRestrictionGuard(BaseGuardrail):
    name = "topic-restriction"

    async def check(self, text: str, config: dict[str, Any]) -> GuardrailResult:
        allowed = set(config.get("allowedTopics", []))
        denied = set(config.get("deniedTopics", []))
        lowered = text.lower()
        for d in denied:
            if d.lower() in lowered:
                return GuardrailResult(
                    passed=False, findings=[GuardrailFinding(type="topic", detail=d)], score=0.2
                )
        if allowed:
            if not any(a.lower() in lowered for a in allowed):
                return GuardrailResult(
                    passed=False, findings=[GuardrailFinding(type="topic", detail="off-topic")], score=0.3
                )
        return GuardrailResult(passed=True)


class ToxicityGuard(BaseGuardrail):
    name = "toxicity-detection"

    async def check(self, text: str, config: dict[str, Any]) -> GuardrailResult:
        lowered = text.lower()
        hits = [w for w in _TOXIC_WORDS if w in lowered]
        if hits:
            return GuardrailResult(
                passed=False,
                findings=[GuardrailFinding(type="toxicity", detail=h) for h in hits],
                score=0.2,
            )
        return GuardrailResult(passed=True)


class FormatValidationGuard(BaseGuardrail):
    name = "format-validation"

    async def check(self, text: str, config: dict[str, Any]) -> GuardrailResult:
        required = config.get("contains")
        if required and required not in text:
            return GuardrailResult(passed=False, findings=[GuardrailFinding(type="format", detail="missing-required")])
        return GuardrailResult(passed=True)


class GuardrailRegistry:
    """Registry of available guardrails."""

    BUILT_IN: ClassVar[dict[str, type[Guardrail]]] = {
        "pii-detection": PIIDetectionGuard,
        "prompt-injection": PromptInjectionGuard,
        "topic-restriction": TopicRestrictionGuard,
        "toxicity-detection": ToxicityGuard,
        "format-validation": FormatValidationGuard,
    }

    def __init__(self) -> None:
        self._registry: dict[str, Guardrail] = {name: cls() for name, cls in self.BUILT_IN.items()}

    def register(self, guardrail: Guardrail) -> None:
        self._registry[guardrail.name] = guardrail

    def get(self, name: str) -> Guardrail:
        g = self._registry.get(name)
        if g is None:
            raise KeyError(f"Unknown guardrail: {name}")
        return g

    async def run_input(self, text: str, guardrails: list[str], configs: dict[str, dict[str, Any]] | None = None) -> GuardrailResult:
        try:
            return await self._run(text, guardrails, configs or {})
        except GuardrailBlockedError as e:
            findings = [GuardrailFinding(**f) for f in (getattr(e, "findings", None) or [])]
            return GuardrailResult(passed=False, findings=findings, score=0.1)

    async def run_output(self, text: str, guardrails: list[str], configs: dict[str, dict[str, Any]] | None = None) -> GuardrailResult:
        try:
            return await self._run(text, guardrails, configs or {})
        except GuardrailBlockedError as e:
            findings = [GuardrailFinding(**f) for f in (getattr(e, "findings", None) or [])]
            return GuardrailResult(passed=False, findings=findings, score=0.1)

    async def _run(self, text: str, guardrails: list[str], configs: dict[str, dict[str, Any]]) -> GuardrailResult:
        results: list[GuardrailResult] = []
        modified = text
        for name in guardrails:
            g = self.get(name)
            res = await g.check(modified, configs.get(name, {}))
            results.append(res)
            if res.modified_text is not None:
                modified = res.modified_text
            if not res.passed:
                raise GuardrailBlockedError(
                    f"Blocked by guardrail '{name}'",
                    guardrail=name,
                    findings=[asdict(f) for f in res.findings],
                )
        return GuardrailResult(
            passed=all(r.passed for r in results),
            modified_text=modified if modified != text else None,
            findings=[f for r in results for f in r.findings],
        )
