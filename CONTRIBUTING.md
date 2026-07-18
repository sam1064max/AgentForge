# Contributing to AgentForge

Thank you for your interest in contributing to AgentForge! This document explains
how to get involved, the development workflow, and the engineering standards we
hold ourselves to.

## 🧭 Ways to Contribute

- **Code** — fix bugs, add features, improve performance.
- **Docs** — improve the README, architecture docs, or tutorials.
- **Examples** — share agent recipes.
- **Issues** — report bugs or propose enhancements.
- **Reviews** — review open pull requests.

## 🏗️ Development Setup

AgentForge uses [`uv`](https://github.com/astral-sh/uv) for environment
management and [`pre-commit`](https://pre-commit.com) for quality gates.

```bash
# Clone
git clone https://github.com/sam1064max/AgentForge.git
cd AgentForge

# Create environment and install dev dependencies
uv sync --all-extras

# Install pre-commit hooks
pre-commit install

# Run the test suite
uv run pytest
```

## 🌿 Branching Strategy

We use **trunk-based development with feature branches** and pull-request review.

| Branch | Purpose |
|---|---|
| `main` | Stable, release-ready code. Never commit directly. |
| `develop` | Integration branch for the next release. |
| `feature/*` | A single feature or fix. |
| `release/*` | Release preparation (version bumps, changelog). |
| `hotfix/*` | Urgent fixes against a released version. |

Workflow:

1. Branch from `develop`: `git checkout -b feature/my-feature develop`.
2. Make small, focused commits.
3. Open a PR against `develop` with a clear description.
4. Ensure CI is green and at least one maintainer approves.
5. Merge via squash or rebase (no direct pushes to `main`/`develop`).

## 📐 Engineering Standards

- **Typed Python** — every module is fully typed (`mypy --strict` clean).
- **Formatting/Linting** — `ruff` + `black` enforced in CI and pre-commit.
- **Testing** — unit + integration + e2e. New features require tests.
- **No placeholders** — no `TODO`, no `pass`-only stubs, no "mock architecture".
- **Observability** — log structured events; add metrics for new hot paths.
- **Documentation** — public modules need docstrings; new subsystems need docs.

## ✅ Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org):

```
feat(runtime): add checkpoint resume for long-running executions
fix(memory): correct tenant scoping on semantic recall
docs(sdk): document AgentContext lifecycle
```

## 🧪 Running Checks Locally

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy sdk libs services
uv run pytest -q
```

## 📄 License

By contributing, you agree that your contributions will be licensed under the
[Apache License 2.0](LICENSE).
