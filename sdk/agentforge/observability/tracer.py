"""In-process tracer.

Emits OpenTelemetry-compatible spans when the `opentelemetry` extras are
installed; otherwise falls back to a no-op span recorder so the SDK runs with
zero dependencies. Spans are also collected locally for testing/inspection.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from agentforge.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: str | None = None
    start_ms: float = 0.0
    end_ms: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        return max(0.0, self.end_ms - self.start_ms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
        }


class Tracer:
    """Lightweight tracer with optional OTel export."""

    def __init__(self, *, trace_id: str | None = None, enable_otel: bool = False) -> None:
        self.trace_id = trace_id or uuid.uuid4().hex
        self._enable_otel = enable_otel
        self._spans: list[Span] = []
        self._lock = threading.RLock()
        self._otel_tracer = None
        if enable_otel:
            try:
                from opentelemetry import trace as otel_trace

                self._otel_tracer = otel_trace.get_tracer("agentforge")
            except Exception as exc:  # noqa: BLE001
                logger.warning("otel unavailable", extra={"attributes": {"error": str(exc)}})

    def start_span(self, name: str, *, parent_id: str | None = None,
                   attributes: dict[str, Any] | None = None) -> Span:
        span = Span(
            name=name,
            trace_id=self.trace_id,
            span_id=uuid.uuid4().hex[:16],
            parent_id=parent_id,
            start_ms=time.monotonic() * 1000,
            attributes=attributes or {},
        )
        if self._otel_tracer is not None:
            self._otel_tracer.start_span(name)
        return span

    def end_span(self, span: Span) -> None:
        span.end_ms = time.monotonic() * 1000
        with self._lock:
            self._spans.append(span)

    def record_event(self, span: Span, name: str, attributes: dict[str, Any] | None = None) -> None:
        span.events.append({"name": name, "attributes": attributes or {}})

    def spans(self) -> list[Span]:
        with self._lock:
            return list(self._spans)

    def export(self) -> list[dict[str, Any]]:
        with self._lock:
            return [s.to_dict() for s in self._spans]
