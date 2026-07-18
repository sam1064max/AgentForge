# SPDX-License-Identifier: Apache-2.0
"""Audit event emission and immutable audit-log store."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AuditEvent:
    id: str
    timestamp: float
    tenant_id: str
    actor_type: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str | None
    outcome: str
    details: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "tenant_id": self.tenant_id,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "outcome": self.outcome,
            "details": self.details,
            "trace_id": self.trace_id,
        }


class AuditLogger:
    """Append-only audit log. Production stores these in an immutable,
    partitioned PostgreSQL table or ClickHouse; this in-memory version is for
    local runs, tests and the control-plane demo."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(
        self,
        *,
        tenant_id: str,
        actor_type: str,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        outcome: str = "success",
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=f"aud-{uuid.uuid4().hex[:12]}",
            timestamp=time.time(),
            tenant_id=tenant_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            details=details or {},
            trace_id=trace_id,
        )
        self._events.append(event)
        return event

    def query(self, *, tenant_id: str | None = None, action: str | None = None) -> list[AuditEvent]:
        return [
            e for e in self._events
            if (tenant_id is None or e.tenant_id == tenant_id)
            and (action is None or e.action == action)
        ]
