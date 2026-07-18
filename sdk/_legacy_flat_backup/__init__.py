"""AgentForge — Enterprise Agent Platform SDK.

The AgentForge SDK provides a typed, Pythonic interface for building,
governing, and operating AI agents at scale. It is the primary developer
surface for the AgentForge platform.

Typical usage::

    from agentforge import Agent, Tool, ModelConfig
    from agentforge.runtime import AgentContext

    @Agent(name="greeter", version="1.0.0",
           model=ModelConfig(provider="openai", model="gpt-4o-mini"))
    class Greeter:
        def __init__(self, ctx: AgentContext) -> None:
            self.ctx = ctx

        @Agent.on_message
        async def handle(self, message: str) -> str:
            return await self.ctx.llm.generate(
                messages=[{"role": "user", "content": message}]
            )
"""

from __future__ import annotations

__version__ = "0.1.0"

from agentforge.agent import Agent, agent
from agentforge.exceptions import (
    AgentForgeError,
    AgentNotFoundError,
    ConfigurationError,
    ExecutionError,
    GuardrailError,
    ProviderError,
    ToolError,
    ValidationError,
)
from agentforge.gateway import ModelConfig, RoutingStrategy
from agentforge.models import Message, ToolCall, ToolDefinition
from agentforge.runtime import AgentContext, ExecutionResult
from agentforge.tool import Tool, tool

__all__ = [
    "__version__",
    # Core decorators
    "Agent",
    "agent",
    "Tool",
    "tool",
    # Runtime
    "AgentContext",
    "ExecutionResult",
    # Models
    "Message",
    "ToolCall",
    "ToolDefinition",
    "ModelConfig",
    "RoutingStrategy",
    # Exceptions
    "AgentForgeError",
    "AgentNotFoundError",
    "ConfigurationError",
    "ExecutionError",
    "GuardrailError",
    "ProviderError",
    "ToolError",
    "ValidationError",
]
