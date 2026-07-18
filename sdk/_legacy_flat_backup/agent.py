"""The ``@Agent`` decorator and agent definition model.

Agents are declared with the :func:`Agent` class decorator. The decorator
captures metadata (name, version, model, guardrails, tools) and registers the
class so it can be discovered and executed by the runtime.

Example::

    @Agent(name="order-agent", version="1.2.0",
           model=ModelConfig(provider="openai", model="gpt-4o"))
    class OrderAgent:
        def __init__(self, ctx: AgentContext) -> None:
            self.ctx = ctx

        @Agent.on_message
        async def handle(self, message: str) -> str:
            ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from agentforge.gateway import ModelConfig
from agentforge.registry import registry


@dataclass
class AgentDefinition:
    """Captured metadata for an agent class."""

    cls: type
    name: str
    version: str
    model: ModelConfig | None = None
    description: str = ""
    guardrails: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    prompts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    handlers: dict[str, Callable[..., Any]] = field(default_factory=dict)

    def instantiate(self, ctx: Any) -> Any:
        return self.cls(ctx)

    @classmethod
    def run(cls, definition: "AgentDefinition", message: str, **kwargs: Any) -> Any:
        """Execute this agent on a message.

        When called as ``Greeter.run("hi")`` without an active event loop, it
        runs synchronously and returns an :class:`ExecutionResult`. When awaited
        inside an async context, it returns the coroutine for ``execute_agent``.
        """
        from agentforge.runtime.engine import execute_agent, run_agent_sync

        try:
            import asyncio

            asyncio.get_running_loop()
            return execute_agent(definition, message=message, **kwargs)
        except RuntimeError:
            return run_agent_sync(definition, message=message, **kwargs)


def Agent(  # noqa: N802 - decorators are conventionally Capitalized
    *,
    name: str,
    version: str = "0.1.0",
    model: ModelConfig | None = None,
    description: str = "",
    guardrails: list[str] | None = None,
    tools: list[str] | None = None,
    memory: dict[str, Any] | None = None,
    prompts: dict[str, str] | None = None,
    **metadata: Any,
) -> Callable[[type], type]:
    """Class decorator that registers an agent definition."""

    def wrapper(cls: type) -> type:
        definition = AgentDefinition(
            cls=cls,
            name=name,
            version=version,
            model=model,
            description=description,
            guardrails=list(guardrails or []),
            tools=list(tools or []),
            memory=dict(memory or {}),
            prompts=dict(prompts or {}),
            metadata=dict(metadata),
            handlers=getattr(cls, "__af_handlers__", {}),
        )
        cls.__af_definition__ = definition  # type: ignore[attr-defined]

        # Convenience: ``Greeter.run("hi")`` executes the agent. Bound as a
        # classmethod so the implied first arg is the class, not the message.
        def _run(cls_: type, message: str, **kwargs: Any) -> Any:
            return AgentDefinition.run(definition, message, **kwargs)

        cls.run = classmethod(_run)  # type: ignore[attr-defined]
        registry.register_agent(definition)
        return cls

    return wrapper


# Function-form alias for users who prefer ``@agent(...)``.
agent = Agent


def on_message(func: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a method as the primary message handler."""
    handlers = getattr(func.__qualname__.split(".")[0], "__af_handlers__", None)
    # Handlers are attached at class-decoration time; store on the function.
    func.__af_on_message__ = True  # type: ignore[attr-defined]
    return func


def on_tool_call(tool_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a method as the handler for a specific tool call."""

    def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        func.__af_on_tool_call__ = tool_name  # type: ignore[attr-defined]
        return func

    return wrapper


def on_escalation(func: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a method as the human-escalation handler."""
    func.__af_on_escalation__ = True  # type: ignore[attr-defined]
    return func


def system_prompt(func: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a method as the system-prompt provider."""
    func.__af_system_prompt__ = True  # type: ignore[attr-defined]
    return func


def _collect_handlers(cls: type) -> dict[str, Callable[..., Any]]:
    """Extract handler methods (decorated) from an agent class."""
    handlers: dict[str, Callable[..., Any]] = {}
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name, None)
        if callable(attr):
            if getattr(attr, "__af_on_message__", False):
                handlers["on_message"] = attr
            if getattr(attr, "__af_on_tool_call__", False):
                handlers[f"tool:{attr.__af_on_tool_call__}"] = attr
            if getattr(attr, "__af_on_escalation__", False):
                handlers["on_escalation"] = attr
            if getattr(attr, "__af_system_prompt__", False):
                handlers["system_prompt"] = attr
    return handlers


# Patch the decorator so handlers are collected when the class is defined.
_original_agent = Agent


def _agent_with_handlers(*args: Any, **kwargs: Any) -> Callable[[type], type]:
    def wrapper(cls: type) -> type:
        cls.__af_handlers__ = _collect_handlers(cls)  # type: ignore[attr-defined]
        return _original_agent(*args, **kwargs)(cls)

    return wrapper


Agent = _agent_with_handlers  # type: ignore[assignment]
agent = Agent

# Expose handler decorators as attributes so `@Agent.on_message` works as shown
# in the README and docs.
Agent.on_message = on_message  # type: ignore[attr-defined]
Agent.on_tool_call = on_tool_call  # type: ignore[attr-defined]
Agent.on_escalation = on_escalation  # type: ignore[attr-defined]
Agent.system_prompt = system_prompt  # type: ignore[attr-defined]
agent.on_message = on_message  # type: ignore[attr-defined]
agent.on_tool_call = on_tool_call  # type: ignore[attr-defined]
agent.on_escalation = on_escalation  # type: ignore[attr-defined]
agent.system_prompt = system_prompt  # type: ignore[attr-defined]
