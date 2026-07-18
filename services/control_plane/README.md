# SPDX-License-Identifier: Apache-2.0
# AgentForge Control Plane

The operational brain of the platform: registers agent definitions and manages
their deployment lifecycle with strict tenant isolation.

## API

All endpoints require an `X-Tenant-Id` header.

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET  | `/healthz` | Liveness probe |
| POST | `/agents` | Register an agent |
| GET  | `/agents` | List agents for the tenant |
| GET  | `/agents/{id}` | Fetch an agent |
| PATCH| `/agents/{id}` | Update an agent |
| DELETE| `/agents/{id}` | Delete an agent |
| POST | `/agents/{id}/deploy` | Deploy an agent (returns a deployment) |
| GET  | `/deployments` | List deployments for the tenant |

## Run

```bash
pip install -e .
uvicorn services.control_plane.app:app --reload --port 8080
```

Example:

```bash
curl -X POST localhost:8080/agents \
  -H "X-Tenant-Id: acme" \
  -H "Content-Type: application/json" \
  -d '{"name":"support","version":"1.0.0","description":"Support","model":"openai/gpt-4o","entrypoint":"examples/order_agent.py","tools":["lookup_order"]}'
```

> The local store is in-memory. Production swaps in PostgreSQL
> (see `docs/adr/0001-postgres-citus-primary-store.md`) behind the same API.
