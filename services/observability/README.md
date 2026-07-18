# SPDX-License-Identifier: Apache-2.0
# AgentForge Observability & Evaluation Gateway

Ingests runtime telemetry from agents, exposes a Prometheus-style scrape
endpoint, and runs quality-gate evaluation runs that decide whether a release
may proceed.

## API

All endpoints require an `X-Tenant-Id` header.

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET  | `/healthz` | Liveness probe |
| POST | `/metrics` | Ingest a metric |
| GET  | `/metrics` | Query metrics for the tenant |
| GET  | `/metrics/prometheus` | Prometheus text exposition |
| POST | `/spans` | Ingest a trace span |
| GET  | `/spans` | Query spans for the tenant |
| POST | `/eval/runs` | Create an evaluation run |
| POST | `/eval/runs/{id}/result` | Submit pass/total results (gates on threshold) |
| GET  | `/eval/runs/{id}` | Fetch an evaluation run |

## Run

```bash
pip install -e .
uvicorn services.observability.app:app --reload --port 8081
```

## Quality gate example

```bash
curl -X POST localhost:8081/eval/runs -H "X-Tenant-Id: acme" \
  -d '{"suite":"regression","threshold":0.8}'
# -> {"run_id":"eval-...", ...}
curl -X POST localhost:8081/eval/runs/$RUN_ID/result -H "X-Tenant-Id: acme" \
  -d '{"cases_total":10,"cases_passed":9}'
# -> {"status":"passed","passed":true}
```

> The local store is in-memory. Production swaps in ClickHouse / Prometheus /
> an OTel collector (see `docs/adr/0007-clickhouse-analytics.md`) behind the same API.
