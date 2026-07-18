# Developer Guide

This guide gets you from zero to a running AgentForge development environment and
explains the everyday workflows.

## 1. Prerequisites

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv)
- Node.js 20+ (only for portals / docs site)
- Docker & Docker Compose (for the full stack)
- `make` (optional, convenience wrappers)

## 2. Quick Start (Local, No Infra)

AgentForge ships with **in-process backends** (memory, cache, vector store,
event bus) so you can run the entire platform without external services.

```bash
uv sync --all-extras
uv run python -c "import agentforge; print(agentforge.__version__)"
```

Run a minimal agent:

```python
import asyncio
from agentforge import Agent, ModelConfig
from agentforge.runtime import AgentContext

@Agent(name="hello", version="1.0.0", model=ModelConfig(provider="mock"))
class Hello:
    def __init__(self, ctx: AgentContext) -> None:
        self.ctx = ctx

    @Agent.on_message
    async def handle(self, message: str) -> str:
        return f"echo: {message}"

asyncio.run(Hello.run("hi"))
```

## 3. Full Stack with Docker

```bash
docker compose up -d
# API gateway on :8000, dev portal on :3000, admin portal on :3001
```

The compose stack wires Postgres, Redis, Qdrant, and Kafka for production-like
behavior. Swap backends in `agentforge.yaml`:

```yaml
backends:
  cache: redis://localhost:6379
  vector: qdrant://localhost:6333
  eventbus: kafka://localhost:9092
```

## 4. Project Layout

```
sdk/agentforge/     # The pip package
libs/agentforge-core/  # Shared abstractions & backends
services/           # FastAPI microservices
examples/           # Runnable examples
docs/               # Documentation & architecture
infra/              # Helm, k8s, docker
tests/              # Integration & e2e
benchmarks/         # Performance suites
```

## 5. Common Tasks

| Task | Command |
|---|---|
| Format code | `uv run ruff format .` |
| Lint | `uv run ruff check .` |
| Type-check | `uv run mypy sdk libs services` |
| Test (unit) | `uv run pytest -m unit` |
| Test (integration) | `uv run pytest -m integration` |
| Test (e2e) | `uv run pytest -m e2e` |
| Build package | `uv build` |
| Build docs | `uv run mkdocs build` |

## 6. Adding a New Tool

```python
from agentforge import Tool

@Tool(name="weather", description="Get current weather", permissions=["env:read"])
async def weather(city: str) -> dict:
    return {"city": city, "temp_c": 21}
```

Register it with the runtime and reference it from an agent manifest.

## 7. Adding a Guardrail

```python
from agentforge.guardrails import Guardrail, GuardrailResult

class NoSecretsGuard(Guardrail):
    name = "no-secrets"

    async def check(self, text: str, config: dict) -> GuardrailResult:
        if "sk-" in text:
            return GuardrailResult(passed=False, reason="API key leaked")
        return GuardrailResult(passed=True)
```

## 8. Testing Philosophy

- **Unit** — pure logic, mocked LLMs/tools (`MockLLM`, `MockTool`).
- **Integration** — real backends via the local stack.
- **E2E** — full execution through the API gateway.

Every feature ships with at least unit coverage and a test that exercises the
public interface.

## 9. Debugging

- Set `AGENTFORGE_LOG_LEVEL=debug`.
- Use `agentforge trace <execution_id>` against a running gateway.
- OTel traces export to the configured collector (or stdout in dev).
