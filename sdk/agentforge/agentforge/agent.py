# SPDX-License-Identifier: Apache-2.0
"""Agent definition decorators and base class.

The :func:`@Agent` decorator turns a plain class into a fully managed agent that
the runtime can load, execute and supervise. Method decorators
(:func:`@Agent.system_prompt`, :func:`@Agent.on_message`, :func:`@Agent.on_tool_call`,
:func:`@Agent.on_escalation`) mark the hooks the runtime invokes.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar

from typing import TYPE_CHECKING

from agentforge.models.config import ModelConfig

if TYPE_CHECKING:
    from agentforge.runtime.context import AgentContext


@dataclass
class AgentSpec:
    """Parsed specification of an agent produced by the decorator."""

    name: str
    version: str
    description: str
    model: ModelConfig
    guardrails: list[str]
    tools: list[str]
    memory: dict[str, Any]
    prompt: str | None
    hooks: dict[str, Callable[..., Any]] = field(default_factory=dict)
    cls: type | None = None


def _method_marker(attr: str):
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(fn, f"__agentforge_{attr}__", True)
        return fn

    return decorator


class _AgentMeta(type):
    """Metaclass that collects marked hooks into ``__agentforge_spec__``."""

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> type:
        cls = super().__new__(mcs, name, bases, namespace)
        if namespace.get("__agentforge_skip_meta__"):
            return cls
        spec = namespace.get("__agentforge_spec__")
        if spec is None:
            # Inherit parent spec if present
            for base in bases:
                spec = getattr(base, "__agentforge_spec__", None)
                if spec is not None:
                    break
            spec = spec or AgentSpec(
                name=name, version="0.0.0", description="", model=ModelConfig(),
                guardrails=[], tools=[], memory={}, prompt=None,
            )
        hooks: dict[str, Callable[..., Any]] = dict(spec.hooks)
        for value in namespace.values():
            if callable(value):
                if getattr(value, "__agentforge_system_prompt__", False):
                    hooks["system_prompt"] = value
                if getattr(value, "__agentforge_on_message__", False):
                    hooks["on_message"] = value
                if getattr(value, "__agentforge_on_tool_call__", False):
                    hooks["on_tool_call"] = value
                if getattr(value, "__agentforge_on_escalation__", False):
                    hooks["on_escalation"] = value
        spec.hooks = hooks
        spec.cls = cls
        cls.__agentforge_spec__ = spec
        return cls


class AgentBase(metaclass=_AgentMeta):
    """Base class every decorated agent inherits from.

    The runtime instantiates the agent with an :class:`AgentContext` and then
    calls the registered ``on_message`` hook to process user input.
    """

    __agentforge_skip_meta__ = True
    __agentforge_spec__: ClassVar[AgentSpec]

    def __init__(self, ctx: AgentContext) -> None:
        self.ctx = ctx

    async def handle(self, message: str) -> AgentContext:
        spec = self.__agentforge_spec__
        hook = spec.hooks.get("on_message")
        if hook is None:
            raise NotImplementedError(
                f"Agent {spec.name} does not define an @Agent.on_message handler"
            )
        if inspect.iscoroutinefunction(hook):
            await hook(self, message)
        else:
            hook(self, message)
        return self.ctx


class Agent:
    """Decorator factory used as ``@Agent(name=..., model=..., ...)``."""

    def __init__(
        self,
        *,
        name: str,
        version: str = "0.1.0",
        description: str = "",
        model: ModelConfig | None = None,
        guardrails: list[str] | None = None,
        tools: list[str] | None = None,
        memory: dict[str, Any] | None = None,
    ) -> None:
        self.spec = AgentSpec(
            name=name,
            version=version,
            description=description,
            model=model or ModelConfig(),
            guardrails=guardrails or [],
            tools=tools or [],
            memory=memory or {},
            prompt=None,
            cls=None,
        )

    def __call__(self, cls: type) -> type:
        # Make the decorated class inherit from AgentBase while preserving any
        # user-declared bases (e.g. a shared Mixin). AgentBase is placed first
        # so its ``__init__``/``handle`` win, matching the common case where the
        # user class does not define its own __init__.
        if AgentBase not in cls.__mro__:
            cls = type(cls.__name__, (AgentBase, *cls.__bases__), dict(cls.__dict__))
        cls.__agentforge_skip_meta__ = True
        cls.__agentforge_spec__ = self.spec
        # Re-run hook collection so newly defined methods are captured.
        spec = self.spec
        hooks: dict[str, Callable[..., Any]] = dict(spec.hooks)
        for value in cls.__dict__.values():
            if callable(value):
                if getattr(value, "__agentforge_system_prompt__", False):
                    hooks["system_prompt"] = value
                if getattr(value, "__agentforge_on_message__", False):
                    hooks["on_message"] = value
                if getattr(value, "__agentforge_on_tool_call__", False):
                    hooks["on_tool_call"] = value
                if getattr(value, "__agentforge_on_escalation__", False):
                    hooks["on_escalation"] = value
        spec.hooks = hooks
        spec.cls = cls
        cls.__agentforge_spec__ = spec
        return cls

    @staticmethod
    def system_prompt(fn: Callable[..., Any]) -> Callable[..., Any]:
        return _method_marker("system_prompt")(fn)

    @staticmethod
    def on_message(fn: Callable[..., Any]) -> Callable[..., Any]:
        return _method_marker("on_message")(fn)

    @staticmethod
    def on_tool_call(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            setattr(fn, "__agentforge_on_tool_call__", True)
            setattr(fn, "__agentforge_tool_name__", name)
            return fn

        return decorator

    @staticmethod
    def on_escalation(fn: Callable[..., Any]) -> Callable[..., Any]:
        return _method_marker("on_escalation")(fn)
