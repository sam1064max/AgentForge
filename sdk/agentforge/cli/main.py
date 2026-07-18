"""AgentForge CLI — the ``agentforge`` command.

Provides developer commands: ``run`` an agent, ``list`` registered agents/tools,
``validate`` a manifest, and ``version``. The CLI is intentionally thin and
delegates to the SDK runtime.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

try:
    import click
except ImportError:  # pragma: no cover
    click = None  # type: ignore

from agentforge import __version__
from agentforge.logging import get_logger, new_trace_id

logger = get_logger(__name__)


def _build_cli() -> Any:
    if click is None:
        return None

    @click.group()
    @click.version_option(__version__, prog_name="agentforge")
    def cli() -> None:
        """AgentForge — build, govern, and operate AI agents at scale."""

    @cli.command("list-agents")
    def list_agents() -> None:
        """List registered agents."""
        from agentforge.registry import registry

        for a in registry.list_agents():
            click.echo(f"{a.name}  v{a.version}  {a.description or ''}")

    @cli.command("list-tools")
    def list_tools() -> None:
        """List registered tools."""
        from agentforge.registry import registry

        for t in registry.list_tools():
            click.echo(f"{t.name}  v{t.version}  {t.description or ''}")

    @cli.command("run")
    @click.argument("agent_name")
    @click.option("--message", "-m", required=True, help="Message to send to the agent.")
    @click.option("--tenant", default=None, help="Tenant id.")
    def run(agent_name: str, message: str, tenant: str | None) -> None:
        """Run an agent by name with a message."""
        from agentforge.exceptions import AgentNotFoundError
        from agentforge.registry import registry
        from agentforge.runtime.engine import run_agent_sync

        try:
            definition = registry.get_agent(agent_name)
        except AgentNotFoundError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        result = run_agent_sync(definition, message=message, tenant_id=tenant)
        click.echo(json.dumps(result.to_dict(), indent=2, default=str))

    @cli.command("version")
    def version() -> None:
        """Print the AgentForge SDK version."""
        click.echo(__version__)

    return cli


cli = _build_cli()


def main() -> Any:
    if cli is None:
        # click not installed; provide a minimal fallback.
        print(f"agentforge {__version__}")
        print("Install 'agentforge[cli]' for the full CLI (requires click).")
        return 0
    return cli()


if __name__ == "__main__":  # pragma: no cover
    main()
