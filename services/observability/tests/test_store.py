# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the observability & evaluation gateway store."""

from __future__ import annotations

from services.observability.store import EvalStatus, ObservabilityStore


def _seed(s: ObservabilityStore) -> None:
    s.record_metric(name="agentforge.llm.tokens_total", kind="counter", value=128,
                    tenant_id="acme", labels={"agent": "support"})
    s.record_span(trace_id="t1", span_id="s1", name="agent.execute", tenant_id="acme",
                  agent_id="support", duration_ms=42.0, status="ok")


def test_metric_ingest_and_query():
    s = ObservabilityStore()
    _seed(s)
    metrics = s.query_metrics(tenant_id="acme", name="agentforge.llm.tokens_total")
    assert len(metrics) == 1
    assert metrics[0].value == 128


def test_metric_tenant_isolation():
    s = ObservabilityStore()
    _seed(s)
    assert s.query_metrics(tenant_id="other") == []


def test_span_query_and_isolation():
    s = ObservabilityStore()
    _seed(s)
    assert len(s.query_spans(tenant_id="acme", agent_id="support")) == 1
    assert s.query_spans(tenant_id="other") == []


def test_eval_gate_passes_above_threshold():
    s = ObservabilityStore()
    run = s.create_eval_run(suite="regression", tenant_id="acme", threshold=0.8)
    run = s.submit_eval_result(run_id=run.run_id, cases_total=10, cases_passed=9)
    assert run is not None
    assert run.status == EvalStatus.PASSED
    assert run.passed is True


def test_eval_gate_fails_below_threshold():
    s = ObservabilityStore()
    run = s.create_eval_run(suite="regression", tenant_id="acme", threshold=0.8)
    run = s.submit_eval_result(run_id=run.run_id, cases_total=10, cases_passed=5)
    assert run.status == EvalStatus.FAILED
    assert run.passed is False


def test_eval_run_unknown():
    s = ObservabilityStore()
    assert s.submit_eval_result(run_id="nope", cases_total=1, cases_passed=1) is None
