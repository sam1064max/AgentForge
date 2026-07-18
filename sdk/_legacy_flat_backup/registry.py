"""In-memory registry for agents and tools.

The registry is the local source of truth during development and is mirrored
to the Agent Registry service in production. It supports discovery by name and
capability.
"""

from __future__ import annotations

from typing import Any

from agentforge.logging import get_logger

logger = get_logger(__name__)


class Registry:
    """A thread-safe registry of named, typed entries."""

    def __init__(self) -> None:
        self._agents: dict[str, Any] = {}
        self._tools: dict[str, Any] = {}
        self._workflows: dict[str, Any] = {}

    # ── Agents ──────────────────────────────────────────────
    def register_agent(self, definition: Any) -> None:
        self._agents[definition.name] = definition
        logger.debug("registered agent", extra={"attributes": {"agent": definition.name}})

    def get_agent(self, name: str) -> Any:
        if name not in self._agents:
            from agentforge.exceptions import AgentNotFoundError

            raise AgentNotFoundError(f"Agent '{name}' is not registered")
        return self._agents[name]

    def list_agents(self) -> list[Any]:
        return list(self._agents.values())

    # ── Tools ───────────────────────────────────────────────
    def register_tool(self, definition: Any) -> None:
        self._tools[definition.name] = definition
        logger.debug("registered tool", extra={"attributes": {"tool": definition.name}})

    def get_tool(self, name: str) -> Any:
        if name not in self._tools:
            from agentforge.exceptions import ConfigurationError

            raise ConfigurationError(f"Tool '{name}' is not registered")
        return self._tools[name]

    def list_tools(self) -> list[Any]:
        return list(self._tools.values())

    # ── Workflows ───────────────────────────────────────────
    def register_workflow(self, definition: Any) -> None:
        self._workflows[definition.name] = definition

    def get_workflow(self, name: str) -> Any:
        return self._workflows[name]

    def list_workflows(self) -> list[Any]:
        return list(self._workflows.values())


# Process-wide singleton registry.
registry = Registry()
