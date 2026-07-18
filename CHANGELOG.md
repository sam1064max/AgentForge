# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-18

### Added

- **Core SDK** (`agentforge`): typed `@Agent`, `@Tool`, and `@Workflow`
  decorators, `AgentContext`, and first-class models for LLM, embeddings,
  memory, and evaluation.
- **Agent Runtime**: execution engine with checkpointing, retries, human-in-the-loop
  pause/resume, and a dead-letter queue.
- **Memory**: short-term (conversation), long-term, semantic (vector), and shared
  team memory, with in-memory and Redis-backed implementations.
- **Prompt Registry**: versioned, variable-driven prompt templates with rendering.
- **Knowledge & RAG**: connector framework, multiple chunking strategies, hybrid
  (vector + BM25) retrieval with Reciprocal Rank Fusion and cross-encoder re-ranking,
  and pluggable vector stores (in-memory, Qdrant-compatible interface).
- **Tool Layer**: tool registry, execution runtime with permission, rate-limit,
  timeout, retry, and circuit-breaker policies.
- **MCP Gateway**: connect to Model Context Protocol servers and expose their
  tools to agents.
- **A2A Communication**: capability-based agent discovery and task delegation.
- **Model Gateway**: unified LLM request schema, provider adapters (OpenAI,
  Anthropic), cost-aware routing, fallback chains, and semantic caching.
- **Guardrails**: PII detection/redaction, prompt-injection detection, factual
  grounding, toxicity, and brand-safety checks.
- **Governance**: declarative policy engine (Rego-style evaluation), multi-level
  approval workflows, and EU AI Act risk classification.
- **Observability**: OpenTelemetry tracing, Prometheus metrics, and structured
  logging with AgentForge semantic conventions.
- **Evaluation**: offline and online metric suites, golden datasets, experiment
  tracking, and HTML/JSON report generation.
- **Portals**: Developer and Admin portal API services (FastAPI) exposing the
  full REST surface.
- **Packaging & Infra**: PyPI package, Dockerfile, Docker Compose stack,
  and Helm chart.
- **CI/CD**: GitHub Actions for lint, type-check, test, coverage, build, and release.
- **Documentation**: README, Architecture (10 parts), ADRs, Developer Guide,
  and API docs.

[0.1.0]: https://github.com/sam1064max/AgentForge/releases/tag/v0.1.0
