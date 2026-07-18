# SPDX-License-Identifier: Apache-2.0
"""AgentForge observability & evaluation gateway.

This service receives runtime telemetry (spans, metrics, logs) from agents,
stores it, and runs evaluation suites that gate releases on quality thresholds.
It is the operational counterpart to the evaluation framework in the SDK
(``agentforge.eval``) and mirrors ``docs/architecture/07-observability-evaluation.md``.

Local implementation uses in-memory stores; production swaps in ClickHouse /
Prometheus / an OTel collector behind the same API (see docs/adr/0007).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class MetricKind(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class EvalStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"


@dataclass
class Metric:
    name: str
    kind: MetricKind
    value: float
    tenant_id: str
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Span:
    trace_id: str
    span_id: str
    name: str
    tenant_id: str
    agent_id: str | None = None
    start_ms: float = field(default_factory=lambda: time.time() * 1000)
    duration_ms: float = 0.0
    status: str = "ok"
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalRun:
    run_id: str
    suite: str
    tenant_id: str
    status: EvalStatus = EvalStatus.PENDING
    cases_total: int = 0
    cases_passed: int = 0
    threshold: float = 0.8
    passed: bool = False
    created_at: float = field(default_factory=time.time)


class ObservabilityStore:
    """In-memory telemetry + evaluation store."""

    def __init__(self) -> None:
        self._metrics: list[Metric] = []
        self._spans: list[Span] = []
        self._evals: dict[str, EvalRun] = {}

    # --- Metrics ----------------------------------------------------------
    def record_metric(self, *, name: str, kind: str, value: float, tenant_id: str,
                      labels: dict[str, str] | None = None) -> Metric:
        m = Metric(name=name, kind=MetricKind(kind), value=value, tenant_id=tenant_id,
                   labels=labels or {})
        self._metrics.append(m)
        return m

    def query_metrics(self, *, tenant_id: str, name: str | None = None) -> list[Metric]:
        return [m for m in self._metrics if m.tenant_id == tenant_id and (name is None or m.name == name)]

    # --- Spans ------------------------------------------------------------
    def record_span(self, *, trace_id: str, span_id: str, name: str, tenant_id: str,
                    agent_id: str | None = None, duration_ms: float = 0.0,
                    status: str = "ok", attributes: dict[str, Any] | None = None) -> Span:
        s = Span(trace_id=trace_id, span_id=span_id, name=name, tenant_id=tenant_id,
                 agent_id=agent_id, duration_ms=duration_ms, status=status,
                 attributes=attributes or {})
        self._spans.append(s)
        return s

    def query_spans(self, *, tenant_id: str, agent_id: str | None = None) -> list[Span]:
        return [s for s in self._spans if s.tenant_id == tenant_id
                and (agent_id is None or s.agent_id == agent_id)]

    # --- Evaluation gate --------------------------------------------------
    def create_eval_run(self, *, suite: str, tenant_id: str, threshold: float = 0.8) -> EvalRun:
        run = EvalRun(run_id=f"eval-{uuid.uuid4().hex[:12]}", suite=suite,
                      tenant_id=tenant_id, status=EvalStatus.PENDING, threshold=threshold)
        self._evals[run.run_id] = run
        return run

    def submit_eval_result(self, *, run_id: str, cases_total: int, cases_passed: int) -> EvalRun | None:
        run = self._evals.get(run_id)
        if run is None:
            return None
        run.cases_total = cases_total
        run.cases_passed = cases_passed
        run.passed = cases_total > 0 and (cases_passed / cases_total) >= run.threshold
        run.status = EvalStatus.PASSED if run.passed else EvalStatus.FAILED
        return run

    def get_eval_run(self, run_id: str) -> EvalRun | None:
        return self._evals.get(run_id)


def _to_dict(rec: Any) -> dict[str, Any]:
    return asdict(rec)
