# AgentForge Roadmap

This roadmap tracks the evolution of AgentForge from the initial open-source
release (`v0.1.0`) toward a production-grade enterprise platform.

## ✅ v0.1.0 — Foundational Release (current)

The initial open-source release delivers a coherent, fully working platform
across all architecture layers, with local backends as defaults so it runs
without external infrastructure.

- [x] **Core SDK** — `@Agent`, `@Tool`, `@Workflow`, `AgentContext`, typed models.
- [x] **Agent Runtime** — execution engine, checkpointing, retries, HITL, DLQ.
- [x] **Memory** — short/long/semantic/shared tiers with pluggable backends.
- [x] **Prompt Registry** — versioned templates with rendering & variables.
- [x] **Knowledge & RAG** — connectors, chunking, hybrid retrieval, re-ranking.
- [x] **Tool Layer** — registry, execution runtime, rate limiting, circuit breakers.
- [x] **MCP Gateway** — connect to MCP servers and expose their tools.
- [x] **A2A Communication** — agent discovery and task delegation.
- [x] **Model Gateway** — unified LLM API, routing, fallback, semantic caching.
- [x] **Guardrails** — PII detection/redaction, prompt-injection, grounding, toxicity.
- [x] **Governance** — policy engine, approvals, compliance classification.
- [x] **Observability** — OpenTelemetry tracing, Prometheus metrics, structured logs.
- [x] **Evaluation** — offline/online metrics, datasets, experiment tracking, reports.
- [x] **Developer & Admin Portals** — FastAPI BFF services (API surface).
- [x] **Packaging** — PyPI (`agentforge`), Docker, Docker Compose, Helm.
- [x] **CI/CD** — lint, type-check, test, coverage, build, release.

## 🔜 v0.2.0 — Durable Orchestration

- [ ] **Temporal** integration for durable workflows (exactly-once, sagas).
- [ ] **A2A Federation** gateway for cross-organization agent networks.
- [ ] **Plugin Marketplace** — share guardrails, tools, connectors, evaluators.
- [ ] **Webhook Framework** — reliable event delivery with DLQ.
- [ ] **Workflow DSL** — `@Step`, `@Parallel`, `@Saga`, `@Condition`.
- [ ] **Multi-Agent Orchestration** patterns (supervisor, pipeline, debate, swarm).

## 🔜 v0.3.0 — Enterprise Hardening

- [ ] **Multi-region DR** — streaming replication and automated failover.
- [ ] **EU AI Act** compliance automation (risk classification + controls).
- [ ] **Self-hosted models** — vLLM + Ray routing.
- [ ] **Advanced ABAC** — attribute-based policy with time/geo constraints.
- [ ] **ClickHouse analytics** — materialized views and dashboards.
- [ ] **Flink stream processing** for real-time cost & quality aggregation.

## 🎯 v1.0.0 — Production Launch

- [ ] SLA-backed multi-tenancy (10,000+ agents, 100+ tenants).
- [ ] SSO (Keycloak), OIDC/SAML federation.
- [ ] Cost-optimization auto-pilot.
- [ ] Benchmark suite & leaderboard.
- [ ] Stable, backward-compatible SDK and CLI (`v1.0`).

## How to Influence the Roadmap

- Open a [Discussion](https://github.com/sam1064max/AgentForge/discussions).
- File an [Issue](https://github.com/sam1064max/AgentForge/issues) with the
  `enhancement` label.
- Contribute a PR against `develop`.
