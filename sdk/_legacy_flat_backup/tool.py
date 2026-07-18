"""The ``@Tool`` decorator and tool definition model.

Tools are the capabilities agents call. The decorator captures the schema
(derived from type hints / docstring), governance metadata, and resilience
policies (rate limit, timeout, retry, circuit breaker).
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from agentforge.registry import registry


@dataclass
class ToolDefinition:
    """Captured metadata for a tool function."""

    func: Callable[..., Any]
    name: str
    description: str
    version: str = "1.0.0"
    permissions: list[str] = field(default_factory=list)
    rate_limit: str | None = None
    timeout: int = 30
    retry_policy: dict[str, Any] = field(default_factory=dict)
    circuit_breaker: dict[str, Any] = field(default_factory=dict)
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    tags: list[str] = field(default_factory=list)

    async def invoke(self, **kwargs: Any) -> Any:
        result = self.func(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result


def Tool(  # noqa: N802
    *,
    name: str,
    description: str = "",
    version: str = "1.0.0",
    permissions: list[str] | None = None,
    rate_limit: str | None = None,
    timeout: int = 30,
    retry_policy: dict[str, Any] | None = None,
    circuit_breaker: dict[str, Any] | None = None,
    requires_approval: bool = False,
    tags: list[str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Function decorator that registers a tool definition."""

    def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        doc = description or (func.__doc__ or "").strip().split("\n")[0]
        definition = ToolDefinition(
            func=func,
            name=name,
            description=doc,
            version=version,
            permissions=list(permissions or []),
            rate_limit=rate_limit,
            timeout=timeout,
            retry_policy=dict(retry_policy or {}),
            circuit_breaker=dict(circuit_breaker or {}),
            requires_approval=requires_approval,
            tags=list(tags or []),
        )
        func.__af_tool__ = definition  # type: ignore[attr-defined]
        registry.register_tool(definition)
        return func

    return wrapper


def tool(*args: Any, **kwargs: Any) -> Any:  # function-form alias
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return Tool()(args[0])
    return Tool(*args, **kwargs)
