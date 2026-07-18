# SPDX-License-Identifier: Apache-2.0
# AgentForge developer tasks.

PYTHON ?= python3
UV ?= uv

.PHONY: help install test test-sdk test-control-plane lint run-example fmt

help:
	@echo "AgentForge make targets:"
	@echo "  install          Install SDK + dev deps"
	@echo "  test             Run all test suites"
	@echo "  test-sdk         Run SDK tests"
	@echo "  test-control-plane  Run control-plane tests"
	@echo "  lint             Run ruff"
	@echo "  run-example      Run the order-agent example"

install:
	cd sdk/agentforge && $(UV) pip install -e ".[dev]" || pip install -e sdk/agentforge[dev]

test: test-sdk test-control-plane

test-sdk:
	cd sdk/agentforge && $(UV) run --with pydantic --with httpx --with pytest python -m pytest tests -q

test-control-plane:
	$(UV) run --with pytest --with fastapi --with pydantic python -m pytest services/control_plane/tests -q

lint:
	$(UV) run --with ruff ruff check sdk/agentforge/agentforge services/control_plane

run-example:
	PYTHONPATH=sdk/agentforge $(UV) run --with pydantic --with httpx python examples/order_agent.py
