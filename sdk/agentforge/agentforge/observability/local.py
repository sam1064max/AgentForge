# SPDX-License-Identifier: Apache-2.0
"""Observability: structured logging, metrics and tracing.

This module defines the :class:`ObservabilitySink` used throughout the SDK and
ships a :class:`LocalObservability` implementation that records spans/metrics/logs
in-process (ideal for local development and tests). Production deployments swap
in an OpenTelemetry-backed sink (``otlp://``) that exports to the collector.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any

from agentforge.interfaces import ObservabilitySink

# AgentForge semantic-convention attribute keys (subset of the architecture).
AGENTFORGE_ATTRIBUTES: dict[str, str] = {
    "agentforge.agent_id": "Unique agent identifier",
    "agentforge.agent_version": "Agent version",
    "agentforge.execution_id": "Unique execution identifier",
    "agentforge.tenant_id": "Tenant identifier",
    "agentforge.llm.model": "Model identifier",
    "agentforge.llm.provider": "Provider name",
    "agentforge.llm.cost_usd": "Cost in USD",
    "agentforge.tool.name": "Tool name",
    "agentforge.guardrail.name": "Guardrail name",
}


class Span:
    """A lightweight span record."""

    def __init__(self, name: str, trace_id: str, parent_id: str | None, **attrs: Any) -> None:
        self.name = name
        self.trace_id = trace_id
        self.span_id = uuid.uuid4().hex[:16]
        self.parent_id = parent_id
        self.attributes: dict[str, Any] = dict(attrs)
        self.start = time.perf_counter()
        self.end: float | None = None
        self.status: str = "ok"

    def finish(self, status: str = "ok") -> None:
        self.end = time.perf_counter()
        self.status = status

    @property
    def duration_ms(self) -> float:
        end = self.end if self.end is not None else time.perf_counter()
        return (end - self.start) * 1000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "attributes": self.attributes,
            "duration_ms": round(self.duration_ms, 3),
            "status": self.status,
        }


class LocalObservability(ObservabilitySink):
    """In-process observability sink. Safe to use without external services."""

    def __init__(self, *, service: str = "agentforge", logger: logging.Logger | None = None) -> None:
        self.service = service
        self._logger = logger or logging.getLogger("agentforge")
        self._spans: list[Span] = []
        self._metrics: dict[str, float] = {}
        self._logs: list[dict[str, Any]] = []
        self._active: dict[int, Span] = {}

    @contextmanager
    def span(self, name: str, **attrs: Any) -> Any:
        parent = self._active.get(id(self))
        trace_id = attrs.pop("trace_id", None) or (parent.trace_id if parent else uuid.uuid4().hex)
        span = Span(name, trace_id, parent.span_id if parent else None, **attrs)
        token = id(self)
        prev = self._active.get(token)
        self._active[token] = span
        try:
            yield span
        except Exception:
            span.finish("error")
            raise
        finally:
            span.finish()
            self._spans.append(span)
            if prev is not None:
                self._active[token] = prev
            else:
                self._active.pop(token, None)

    def record(self, name: str, value: float, **attrs: Any) -> None:
        self._metrics[name] = self._metrics.get(name, 0.0) + value

    def log(self, level: str, message: str, **attrs: Any) -> None:
        record = {
            "timestamp": time.time(),
            "level": level.upper(),
            "service": self.service,
            "message": message,
            **attrs,
        }
        self._logs.append(record)
        getattr(self._logger, level.lower(), self._logger.info)(message, extra={"attrs": attrs})

    # Inspection helpers ---------------------------------------------------
    def spans(self) -> list[Span]:
        return list(self._spans)

    def metrics(self) -> dict[str, float]:
        return dict(self._metrics)

    def logs(self) -> list[dict[str, Any]]:
        return list(self._logs)
