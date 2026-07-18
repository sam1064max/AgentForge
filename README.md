<p align="center">
  <img src="https://raw.githubusercontent.com/sam1064max/AgentForge/main/docs/assets/hero.svg" alt="AgentForge" width="720"/>
</p>

<p align="center">
  <b>The Kubernetes for AI Agents — build, govern, and operate enterprise AI agents at scale.</b>
</p>

<p align="center">
  <a href="https://pypi.org/project/agentforge/"><img src="https://img.shields.io/pypi/v/agentforge.svg" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/agentforge/"><img src="https://img.shields.io/pypi/pyversions/agentforge.svg" alt="Python Versions"></a>
  <a href="https://github.com/sam1064max/AgentForge/actions"><img src="https://img.shields.io/github/actions/workflow/status/sam1064max/AgentForge/ci.yml?branch=main" alt="CI"></a>
  <a href="https://codecov.io/gh/sam1064max/AgentForge"><img src="https://img.shields.io/codecov/c/github/sam1064max/AgentForge" alt="Coverage"></a>
  <a href="https://github.com/sam1064max/AgentForge/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://github.com/sam1064max/AgentForge/releases"><img src="https://img.shields.io/github/v/release/sam1064max/AgentForge" alt="Release"></a>
  <a href="https://agentforge.dev"><img src="https://img.shields.io/badge/docs-agentforge.dev-blue" alt="Docs"></a>
  <a href="https://github.com/sam1064max/AgentForge"><img src="https://img.shields.io/badge/quality-ruff%20%7C%20mypy%20%7C%20black-9cf" alt="Code Quality"></a>
  <a href="https://github.com/sam1064max/AgentForge/discussions"><img src="https://img.shields.io/badge/discussions-welcome-purple" alt="Discussions"></a>
</p>

---

**AgentForge** is an enterprise-grade, open-source platform for building, governing, and operating AI agents
at scale. Just as Kubernetes abstracts infrastructure for containers, AgentForge abstracts the complexity of
LLM orchestration, tool calling, memory, governance, and multi-agent coordination — so thousands of developers
can ship production AI agents with the same confidence they deploy microservices today.

> Built as if it were an internal platform at a Fortune 500. Modular, typed, tested, and deployable from a laptop
> to a multi-region Kubernetes cluster.

## ✨ Why AgentForge?

| Capability | What it gives you |
|---|---|
| **Declarative Agents** | Define agents as versioned YAML manifests (like K8s resources) — git-ops friendly. |
| **Core SDK** | A type-safe Python SDK with `@Agent`, `@Tool`, and `@Workflow` decorators. |
| **Agent Runtime** | Stateful execution engine with checkpointing, retries, HITL, and a dead-letter queue. |
| **Intelligence Layer** | A unified Model Gateway with routing, fallbacks, semantic caching, and cost control. |
| **Memory & RAG** | Short/long/semantic/shared memory, vector store, knowledge connectors, hybrid RAG. |
| **Tool & Integration** | Tool registry, execution runtime, MCP gateway, and A2A agent communication. |
| **Governance** | OPA-style policy engine, approvals, compliance classification (EU AI Act), audit trails. |
| **Observability** | OpenTelemetry tracing, Prometheus metrics, structured logging, full eval framework. |
| **Multi-tenancy** | Isolation at compute, data (RLS), network, secrets, and observability layers. |

## 🏗️ Architecture

AgentForge is organized as a layered monorepo. Each layer is a first-class subsystem with clear interfaces.

```
┌──────────────────────────── DEVELOPER EXPERIENCE ────────────────────────────┐
│  Dev Portal · CLI · SDK · REST/gRPC API                                        │
├──────────────────────────── API GATEWAY & MESH ──────────────────────────────┤
│  Gateway · Rate Limiter · AuthN/AuthZ · Tenant Router                          │
├──────────────────────────── AGENT CONTROL PLANE ─────────────────────────────┤
│  Registry · Builder · Workflow Engine · Scheduler · Marketplace               │
├──────────────────────────── AGENT DATA PLANE (RUNTIME) ──────────────────────┤
│  Runtime · Multi-Agent Orchestrator · Tool Execution · MCP Gateway · A2A       │
├──────────────────────────── INTELLIGENCE LAYER ──────────────────────────────┤
│  Model Gateway · LLM Router · Prompt Registry · RAG Service · Guardrails       │
├──────────────────────────── MEMORY & KNOWLEDGE ──────────────────────────────┤
│  Memory Service · Conversation Store · Vector Store · Knowledge Base           │
├──────────────────────────── GOVERNANCE & SECURITY ───────────────────────────┤
│  Policy Engine · PII Detection · Compliance · Approval Workflows · Secrets     │
├──────────────────────────── OBSERVABILITY ───────────────────────────────────┤
│  Tracing (OTel) · Metrics (Prom) · Logging · Alerting · SLO Monitoring         │
├──────────────────────────── EVALUATION & ANALYTICS ──────────────────────────┤
│  Eval Framework · Experiment Tracking · Business KPIs · Human Feedback        │
└──────────────────────────── INFRASTRUCTURE ──────────────────────────────────┘
```

See [`docs/architecture/`](docs/architecture/) for the 10-part architecture specification and sequence diagrams.

## 📦 Installation

```bash
# Core SDK + runtime
pip install agentforge

# With optional integrations
pip install "agentforge[rag,mcp,observability,cli]"
```

```bash
# Run the full local stack (AgentForge services + dependencies)
docker compose up -d
```

## 🚀 Quick Start

```python
from agentforge import Agent, Tool, ModelConfig
from agentforge.runtime import AgentContext

@Agent(
    name="greeter",
    version="1.0.0",
    model=ModelConfig(provider="openai", model="gpt-4o-mini"),
)
class Greeter:
    def __init__(self, ctx: AgentContext) -> None:
        self.ctx = ctx

    @Agent.on_message
    async def handle(self, message: str) -> str:
        return await self.ctx.llm.generate(
            messages=[{"role": "user", "content": message}],
        )

# Run locally (no external infra required — local backends are the default)
async def main():
    result = await Greeter.run("Hello!")
    print(result.output)
```

Or declaratively with an `agentforge.yaml` manifest:

```yaml
apiVersion: agentforge.io/v1
kind: Agent
metadata:
  name: customer-support-agent
spec:
  model:
    primary: { provider: openai, model: gpt-4o }
    fallback: { provider: anthropic, model: claude-sonnet-4-20250514 }
  memory:
    shortTerm: { type: conversation, maxTurns: 50 }
  tools:
    - name: knowledge-search
      ref: tools/rag-search
  guardrails:
    input: [pii-detection, prompt-injection-detection]
    output: [pii-redaction, hallucination-check]
```

## 🧩 Monorepo Layout

```
AgentForge/
├── apps/            # Service entrypoints (api-gateway, portals, schedulers)
├── services/        # Microservice implementations (control-plane, ...)
├── sdk/             # agentforge — the Python SDK (pip-installable)
├── libs/            # Shared libraries (core, abstractions, storage backends)
├── docs/            # Documentation, architecture, ADRs
├── examples/        # Working examples (order-agent, rag-agent)
├── infra/           # Terraform, Helm, Docker, Kubernetes manifests
├── scripts/         # Build, release, and dev tooling
├── tests/           # Cross-cutting integration & e2e tests
└── benchmarks/      # Performance and quality benchmarks
```

## ✅ What's implemented (v0.1.0)

| Subsystem | Status |
|---|---|
| Core SDK (`@Agent`, `@Tool` decorators, models, types) | ✅ |
| Agent Runtime (execution engine, tool executor, resilience) | ✅ |
| Memory (in-memory provider + facade) | ✅ |
| Knowledge & RAG (chunking, hybrid retriever, context builder) | ✅ |
| Guardrails (PII, prompt-injection, topic, toxicity, format) | ✅ |
| Governance (policy engine + audit) | ✅ |
| Observability (local sink) | ✅ |
| Evaluation (suite, metrics, datasets) | ✅ |
| Control Plane (agent registry + deployment lifecycle API) | ✅ |
| Examples (order-agent, rag-agent) | ✅ |
| Packaging (Dockerfiles, Helm chart) + CI | ✅ |

> Backends (PostgreSQL, Qdrant, Kafka, Temporal) are abstracted behind
> interfaces with local-friendly in-memory/mock defaults, so the platform runs
> with zero external services. See `docs/adr/`.

## 🧪 Examples

| Example | Description |
|---|---|
| [`order-agent`](examples/order-agent.py) | Tool-using order-status agent (end-to-end vs mock gateway) |
| [`rag-agent`](examples/rag_agent.py) | Chunking + hybrid retrieval + context construction demo |

## 📊 Roadmap

See [`ROADMAP.md`](ROADMAP.md). Highlights:

- [x] **v0.1.0** — Core SDK, Runtime, Memory, Tools/MCP, Model Gateway, RAG, Eval, Observability, Governance, Portals, Packaging, CI/CD.
- [ ] **v0.2.0** — Temporal-based durable workflows, A2A federation, plugin marketplace.
- [ ] **v0.3.0** — Multi-region DR, EU AI Act compliance automation, self-hosted vLLM routing.
- [ ] **v1.0.0** — Production SLAs, enterprise SSO, cost-optimization auto-pilot.

## 🤝 Contributing

We welcome contributions. See [`CONTRIBUTING.md`](CONTRIBUTING.md), the
[`ARCHITECTURE.md`](docs/ARCHITECTURE.md), and the [Developer Guide](docs/DEVELOPER_GUIDE.md).
Please read the [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

## 🔐 Security

Report vulnerabilities privately per our [Security Policy](SECURITY.md). We use
defense-in-depth: policy gating, PII detection, audit logging, and tenant isolation.

## 📄 License

AgentForge is licensed under the [Apache License 2.0](LICENSE).

---

<p align="center">
  Built by the AgentForge team · <a href="https://agentforge.dev">agentforge.dev</a> · <a href="https://github.com/sam1064max/AgentForge/discussions">Discussions</a>
</p>
