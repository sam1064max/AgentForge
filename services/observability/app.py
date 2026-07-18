# SPDX-License-Identifier: Apache-2.0
"""FastAPI application for the AgentForge observability & evaluation gateway.

Ingests metrics and spans, exposes a Prometheus-style scrape endpoint, and runs
quality-gate evaluation runs that decide whether a release may proceed.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Header

from services.observability.store import (
    MetricKind,
    ObservabilityStore,
    EvalStatus,
)

app = FastAPI(title="AgentForge Observability & Eval Gateway", version="0.1.0")
store = ObservabilityStore()


def _tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    return x_tenant_id


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/metrics")
async def post_metric(body: dict[str, Any], tenant_id: str = _tenant_id()):
    try:
        m = store.record_metric(
            name=body["name"], kind=body.get("kind", "gauge"),
            value=float(body["value"]), tenant_id=tenant_id,
            labels=body.get("labels"),
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _dict(m)


@app.get("/metrics")
async def get_metrics(name: str | None = None, tenant_id: str = _tenant_id()):
    return [_dict(m) for m in store.query_metrics(tenant_id=tenant_id, name=name)]


@app.get("/metrics/prometheus")
async def prometheus(tenant_id: str = _tenant_id()) -> str:
    """Minimal Prometheus text exposition for the tenant's gauges/counters."""
    lines: list[str] = []
    for m in store.query_metrics(tenant_id=tenant_id):
        label_str = ",".join(f'{k}="{v}"' for k, v in m.labels.items())
        lines.append(f'agentforge_{m.name}{{{label_str}}} {m.value}')
    return "\n".join(lines) + "\n"


@app.post("/spans")
async def post_span(body: dict[str, Any], tenant_id: str = _tenant_id()):
    try:
        s = store.record_span(
            trace_id=body["trace_id"], span_id=body["span_id"], name=body["name"],
            tenant_id=tenant_id, agent_id=body.get("agent_id"),
            duration_ms=float(body.get("duration_ms", 0.0)), status=body.get("status", "ok"),
            attributes=body.get("attributes"),
        )
    except KeyError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _dict(s)


@app.get("/spans")
async def get_spans(agent_id: str | None = None, tenant_id: str = _tenant_id()):
    return [_dict(s) for s in store.query_spans(tenant_id=tenant_id, agent_id=agent_id)]


@app.post("/eval/runs")
async def create_eval_run(body: dict[str, Any], tenant_id: str = _tenant_id()):
    run = store.create_eval_run(
        suite=body["suite"], tenant_id=tenant_id,
        threshold=float(body.get("threshold", 0.8)),
    )
    return _dict(run)


@app.post("/eval/runs/{run_id}/result")
async def submit_eval_result(run_id: str, body: dict[str, Any], tenant_id: str = _tenant_id()):
    run = store.submit_eval_result(
        run_id=run_id, cases_total=int(body["cases_total"]),
        cases_passed=int(body["cases_passed"]),
    )
    if run is None or run.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="eval run not found")
    return _dict(run)


@app.get("/eval/runs/{run_id}")
async def get_eval_run(run_id: str, tenant_id: str = _tenant_id()):
    run = store.get_eval_run(run_id)
    if run is None or run.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="eval run not found")
    return _dict(run)


def _dict(rec: Any) -> dict[str, Any]:
    import dataclasses

    return dataclasses.asdict(rec)
