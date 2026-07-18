# AgentForge Architecture

This document is the entry point to the AgentForge architecture. AgentForge is
the "Kubernetes for AI Agents" — a control plane and data plane for building,
deploying, governing, and operating AI agents at enterprise scale.

## Design Philosophy

1. Agents are first-class citizens, not scripts.
2. Every agent is observable, governable, auditable.
3. Infrastructure is invisible to agent developers.
4. Multi-tenancy and isolation are non-negotiable.
5. LLM providers are interchangeable commodities.
6. Memory is a managed service, not an afterthought.
7. Evaluation is continuous, not a one-time gate.
8. Cost is a first-class metric alongside latency.
9. Human oversight is built-in, not bolted on.
10. Agents declare intent, not implementation.

## Layered Architecture

```
DEVELOPER EXPERIENCE ─ SDK · CLI · Portals · REST/gRPC API
API GATEWAY & MESH  ─ Gateway · Rate Limit · AuthN/AuthZ · Tenant Router
CONTROL PLANE       ─ Registry · Builder · Workflow · Scheduler · Marketplace
DATA PLANE          ─ Runtime · Multi-Agent · Tool Execution · MCP · A2A
INTELLIGENCE        ─ Model Gateway · LLM Router · Prompts · RAG · Guardrails
MEMORY & KNOWLEDGE  ─ Memory · Conversation · Vector · Knowledge Base
GOVERNANCE          ─ Policy Engine · PII · Compliance · Approvals · Secrets
OBSERVABILITY       ─ Tracing · Metrics · Logging · Alerting · SLO
EVALUATION          ─ Eval Framework · Experiments · KPIs · Feedback
INFRASTRUCTURE      ─ K8s · Event Bus · Object Store · DB · Cache
```

## Detailed Specifications

The full architecture is described in ten parts under [`docs/architecture/`](architecture/):

| Part | Document | Focus |
|---|---|---|
| 1 | [01-high-level-architecture.md](architecture/01-high-level-architecture.md) | Philosophy, C4 Context, Tech Stack, Multi-Tenancy |
| 2 | [02-core-platform-subsystems.md](architecture/02-core-platform-subsystems.md) | SDK, Runtime, Scheduler, Workflow, Multi-Agent |
| 3 | [03-memory-knowledge-rag.md](architecture/03-memory-knowledge-rag.md) | Memory, Vector Store, Knowledge Base, RAG |
| 4 | [04-tool-integration-layer.md](architecture/04-tool-integration-layer.md) | Tools, MCP, A2A, Prompts |
| 5 | [05-intelligence-layer.md](architecture/05-intelligence-layer.md) | Model Gateway, Routing, Cost, Caching, Guardrails |
| 6 | [06-governance-security.md](architecture/06-governance-security.md) | Policy, Compliance, Approvals, Identity, Secrets |
| 7 | [07-observability-evaluation.md](architecture/07-observability-evaluation.md) | Tracing, Metrics, Logging, Eval, KPIs |
| 8 | [08-developer-experience.md](architecture/08-developer-experience.md) | Portals, APIs, Webhooks, Plugins, Marketplace |
| 9 | [09-database-event-architecture.md](architecture/09-database-event-architecture.md) | DB Schema, Events, DDD, State Machines |
| 10 | [10-operational-excellence.md](architecture/10-operational-excellence.md) | DR, Scaling, Cost, Roadmap |

## Architecture Decision Records (ADRs)

Key technology decisions are captured as ADRs under [`docs/adr/`](adr/):

- [ADR-001](adr/0001-postgres-citus-primary-store.md) — PostgreSQL + Citus for primary store
- [ADR-002](adr/0002-temporal-workflow.md) — Temporal for durable workflows
- [ADR-003](adr/0003-kafka-event-bus.md) — Kafka for the event bus
- [ADR-004](adr/0004-litellm-model-gateway.md) — LiteLLM as the Model Gateway base
- [ADR-005](adr/0005-qdrant-vector-store.md) — Qdrant for vector storage
- [ADR-006](adr/0006-opa-policy-engine.md) — OPA for the policy engine
- [ADR-007](adr/0007-clickhouse-analytics.md) — ClickHouse for analytics
- [ADR-008](adr/0008-keycloak-identity.md) — Keycloak for identity
- [ADR-009](adr/0009-langgraph-agents.md) — LangGraph for agent state machines
- [ADR-010](adr/0010-redis-caching.md) — Redis Cluster for caching
- [ADR-011](adr/0011-hybrid-tenant-isolation.md) — Hybrid tenant isolation
- [ADR-012](adr/0012-event-driven-cqrs.md) — Event-driven with CQRS

## Implementation Mapping

The open-source `v0.1.0` release realizes this architecture in a Python monorepo:

- `sdk/` → the `agentforge` pip package (SDK + runtime + memory + tools + gateway + eval).
- `services/` → FastAPI microservices (runtime, model-gateway, portals, scheduler).
- `libs/` → shared abstractions and pluggable storage backends.
- Infra components (Postgres, Redis, Qdrant, Kafka, Temporal) are abstracted behind
  interfaces with **local, in-process backends** as defaults, so the platform runs
  end-to-end without external infrastructure. Production deployments swap in the
  real backends via configuration.
