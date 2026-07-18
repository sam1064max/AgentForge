# SPDX-License-Identifier: Apache-2.0
"""Policy engine: declarative, OPA-style evaluation with a local evaluator.

The architecture specifies OPA/Rego as the policy engine. This module provides a
pluggable :class:`PolicyEngine` interface plus a :class:`LocalPolicyEngine` that
evaluates a safe subset of policy expressions locally — sufficient for local
development, tests and the control-plane demo. Production deployments register
an OPA-backed engine behind the same interface.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Any, Callable

from agentforge.errors import PolicyDeniedError
from agentforge.interfaces import PolicyEngine
from agentforge.types import Decision, PolicyDecision


@dataclass(slots=True)
class Policy:
    """A named policy with an evaluator callable."""

    id: str
    description: str
    actions: list[str]
    evaluate: Callable[[dict[str, Any]], Decision]
    priority: int = 100


class LocalPolicyEngine(PolicyEngine):
    """Registry of policies evaluated against an action + context document."""

    def __init__(self) -> None:
        self._policies: list[Policy] = []

    def register(self, policy: Policy) -> None:
        self._policies.append(policy)
        self._policies.sort(key=lambda p: p.priority)

    async def evaluate(self, *, policy: str | None, action: str, context: dict[str, Any]) -> PolicyDecision:
        relevant = [p for p in self._policies if action in p.actions and (policy is None or p.id == policy)]
        reasons: list[str] = []
        for p in relevant:
            decision = p.evaluate(context)
            if decision == Decision.DENY:
                return PolicyDecision(Decision.DENY, reasons=[f"denied by {p.id}: {p.description}"], policy_id=p.id)
            reasons.append(f"allowed by {p.id}")
        return PolicyDecision(Decision.ALLOW, reasons=reasons)

    async def must_allow(self, *, action: str, context: dict[str, Any]) -> None:
        decision = await self.evaluate(policy=None, action=action, context=context)
        if not decision.allowed:
            raise PolicyDeniedError(
                "Policy denied action",
                policy_id=decision.policy_id,
                reason="; ".join(decision.reasons),
            )


# ── Common policy builders ─────────────────────────────────────────────────
def deny_if(predicate: Callable[[dict[str, Any]], bool], *, policy_id: str, description: str, actions: list[str]) -> Policy:
    def evaluate(ctx: dict[str, Any]) -> Decision:
        return Decision.DENY if predicate(ctx) else Decision.ALLOW

    return Policy(id=policy_id, description=description, actions=actions, evaluate=evaluate)


def require_guardrails(policy_id: str = "required-guardrails") -> Policy:
    """Deny deployment unless all required guardrails are configured."""

    def evaluate(ctx: dict[str, Any]) -> Decision:
        agent = ctx.get("agent", {})
        configured = {g for g in agent.get("guardrails", [])}
        required = set(ctx.get("required_guardrails", []))
        missing = required - configured
        return Decision.DENY if missing else Decision.ALLOW

    return Policy(
        id=policy_id,
        description="All required guardrails must be present on the agent",
        actions=["agent.deploy", "agent.register"],
        evaluate=evaluate,
    )


def tenant_isolation(policy_id: str = "tenant-isolation") -> Policy:
    """Deny cross-tenant resource access."""

    def evaluate(ctx: dict[str, Any]) -> Decision:
        resource_tenant = ctx.get("resource", {}).get("tenant_id")
        request_tenant = ctx.get("tenant_id")
        if resource_tenant and request_tenant and resource_tenant != request_tenant:
            return Decision.DENY
        return Decision.ALLOW

    return Policy(
        id=policy_id,
        description="Resources may only be accessed within the owning tenant",
        actions=["tool.execute", "memory.recall", "knowledge.search"],
        evaluate=evaluate,
    )


def rate_limit_guard(max_per_minute: int = 1000, policy_id: str = "rate-limit") -> Policy:
    def evaluate(ctx: dict[str, Any]) -> Decision:
        count = ctx.get("request_count", 0)
        return Decision.DENY if count > max_per_minute else Decision.ALLOW

    return Policy(
        id=policy_id,
        description=f"Reject more than {max_per_minute} requests/minute",
        actions=["llm.chat", "tool.execute"],
        evaluate=evaluate,
    )
