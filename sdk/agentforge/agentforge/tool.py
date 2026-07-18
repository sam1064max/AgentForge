# SPDX-License-Identifier: Apache-2.0
"""Tool definition decorator and base class.

The :func:`@Tool` decorator registers a function as a callable agent tool. The
runtime validates the schema, enforces permissions/rate limits and records usage
before invoking the underlying coroutine or function.
"""

from __future__ import annotations

import functools
import inspect
import typing
from dataclasses import dataclass, field
from typing import Any, Callable

from agentforge.models.config import CircuitBreakerConfig, RateLimitConfig, RetryConfig
from agentforge.types import ToolResult


@dataclass
class ToolSpec:
    """Parsed specification of a tool produced by the decorator."""

    name: str
    description: str
    permissions: list[str]
    rate_limit: RateLimitConfig | None
    timeout: int
    retry_policy: RetryConfig
    circuit_breaker: CircuitBreakerConfig
    execution_type: str
    endpoint: str | None
    fn: Callable[..., Any]
    schema: dict[str, Any] = field(default_factory=dict)


def _build_json_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    """Best-effort JSON schema generation from type hints + docstring."""
    sig = inspect.signature(fn)
    try:
        hints = typing.get_type_hints(fn)
    except Exception:  # noqa: BLE001
        hints = {}
    doc = inspect.getdoc(fn) or ""
    properties: dict[str, Any] = {}
    required: list[str] = []
    for pname, param in sig.parameters.items():
        if pname in ("self", "ctx", "context"):
            continue
        annotation = hints.get(pname, param.annotation)
        ptype = _json_type(annotation)
        prop: dict[str, Any] = {"type": ptype}
        prop["description"] = _extract_param_doc(doc, pname)
        properties[pname] = prop
        if param.default is inspect.Parameter.empty:
            required.append(pname)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _json_type(annotation: Any) -> str:
    import typing as _t

    if annotation is inspect.Parameter.empty or annotation is None:
        return "string"
    origin = getattr(annotation, "__origin__", None)
    if annotation is int or annotation is _t.get_origin(int):
        return "integer"
    if annotation is float:
        return "number"
    if annotation is bool:
        return "boolean"
    if annotation is str:
        return "string"
    if annotation in (list, tuple) or origin in (list, tuple):
        return "array"
    if annotation is dict or origin is dict:
        return "object"
    # Handle string annotations like "bool" from __future__ imports.
    name = getattr(annotation, "__name__", str(annotation))
    return {"int": "integer", "float": "number", "bool": "boolean", "str": "string",
            "list": "array", "dict": "object"}.get(name, "string")


def _extract_param_doc(doc: str, param: str) -> str:
    for line in doc.splitlines():
        line = line.strip()
        if line.startswith(f":param {param}") or line.startswith(f"{param}:"):
            return line.split(":", 1)[-1].strip()
    return ""


class Tool:
    """Decorator factory used as ``@Tool(name=..., description=..., ...)``."""

    def __init__(
        self,
        *,
        name: str,
        description: str = "",
        permissions: list[str] | None = None,
        rate_limit: str | None = "100/min",
        timeout: int = 30,
        retry_policy: dict[str, Any] | None = None,
        circuit_breaker: dict[str, Any] | None = None,
        execution_type: str = "function",
        endpoint: str | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.permissions = permissions or []
        rpm = None
        if rate_limit:
            try:
                rpm = int(str(rate_limit).split("/")[0])
            except ValueError:
                rpm = 60
        self.rate_limit = RateLimitConfig(requests_per_minute=rpm) if rpm else None
        self.timeout = timeout
        self.retry_policy = RetryConfig(**(retry_policy or {}))
        self.circuit_breaker = CircuitBreakerConfig(**(circuit_breaker or {}))
        self.execution_type = execution_type
        self.endpoint = endpoint

    def __call__(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        spec = ToolSpec(
            name=self.name,
            description=self.description or (inspect.getdoc(fn) or "").splitlines()[0] if inspect.getdoc(fn) else "",
            permissions=self.permissions,
            rate_limit=self.rate_limit,
            timeout=self.timeout,
            retry_policy=self.retry_policy,
            circuit_breaker=self.circuit_breaker,
            execution_type=self.execution_type,
            endpoint=self.endpoint,
            fn=fn,
            schema=_build_json_schema(fn),
        )

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if inspect.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            return fn(*args, **kwargs)

        wrapper.__agentforge_tool__ = True  # type: ignore[attr-defined]
        wrapper.__agentforge_spec__ = spec  # type: ignore[attr-defined]
        return wrapper


def get_tool_spec(fn: Callable[..., Any]) -> ToolSpec:
    spec = getattr(fn, "__agentforge_spec__", None)
    if spec is None:
        raise ValueError("Function is not decorated with @Tool")
    return spec


def is_tool(fn: Callable[..., Any]) -> bool:
    return getattr(fn, "__agentforge_tool__", False)
