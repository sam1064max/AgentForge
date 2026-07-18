# SPDX-License-Identifier: Apache-2.0
"""AgentForge SDK public API.

Importing from the top-level ``agentforge`` package gives access to the core
developer surface: agents, tools, memory, prompts, the model gateway, runtime,
observability, governance, evaluation and the CLI.
"""

from __future__ import annotations

from agentforge.agent import Agent, AgentBase, AgentSpec
from agentforge.tool import Tool, ToolSpec, get_tool_spec, is_tool
from agentforge.models import (
    ModelConfig,
    ModelGateway,
    MockProvider,
    RoutingStrategy,
)
from agentforge.memory import Memory
from agentforge.prompt import PromptRegistry, PromptTemplate, PromptVariable
from agentforge.runtime import AgentContext, AgentRuntime, ToolExecutor
from agentforge.guardrail import GuardrailRegistry
from agentforge.governance import AuditLogger, LocalPolicyEngine, Policy
from agentforge.observability import LocalObservability
from agentforge.errors import AgentForgeError
from agentforge.version import __version__

__all__ = [
    "__version__",
    "Agent",
    "AgentBase",
    "AgentSpec",
    "Tool",
    "ToolSpec",
    "get_tool_spec",
    "is_tool",
    "ModelConfig",
    "ModelGateway",
    "MockProvider",
    "RoutingStrategy",
    "Memory",
    "PromptRegistry",
    "PromptTemplate",
    "PromptVariable",
    "AgentContext",
    "AgentRuntime",
    "ToolExecutor",
    "GuardrailRegistry",
    "AuditLogger",
    "LocalPolicyEngine",
    "Policy",
    "LocalObservability",
    "AgentForgeError",
]
