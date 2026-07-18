# SPDX-License-Identifier: Apache-2.0
"""Testing utilities: mock LLM/tool/memory and an agent test harness."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from agentforge.models.llm import LLMRequest, LLMResponse, Message, ToolCall
from agentforge.runtime.execution import AgentRuntime, ToolExecutor


class MockLLM:
    """Scripted LLM for tests. Returns queued responses in order."""

    def __init__(self, responses: list[str] | None = None, tool_calls: list[ToolCall] | None = None) -> None:
        self._responses = list(responses or [])
        self._tool_calls = list(tool_calls or [])
        self.calls: list[LLMRequest] = []

    async def chat(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        if self._tool_calls:
            tc = self._tool_calls.pop(0)
            return LLMResponse(
                message=Message(role="assistant", content="", tool_calls=[asdict(tc)]),
                tool_calls=[tc], model="mock", provider="mock",
            )
        text = self._responses.pop(0) if self._responses else "[mock] ok"
        return LLMResponse(message=Message(role="assistant", content=text), model="mock", provider="mock")


class MockTool:
    """Returns a fixed value or raises, for deterministic tool tests."""

    def __init__(self, return_value: Any = None, side_effect: Exception | None = None) -> None:
        self.return_value = return_value
        self.side_effect = side_effect
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.side_effect is not None:
            raise self.side_effect
        return self.return_value


class AgentTestHarness:
    """Runs an agent spec end-to-end against mocked collaborators."""

    def __init__(self, spec: Any) -> None:
        self._spec = spec
        self.runtime: AgentRuntime | None = None
        self.mocks: dict[str, Any] = {}

    def bind(self, runtime: AgentRuntime) -> "AgentTestHarness":
        self.runtime = runtime
        return self

    def mock_llm(self, llm: MockLLM) -> None:
        self.mocks["llm"] = llm

    def mock_tool(self, name: str, tool: MockTool) -> None:
        self.mocks.setdefault("tools", {})[name] = tool

    async def send(self, message: str, *, tenant_id: str = "test", **kw: Any) -> Any:
        if self.runtime is None:
            self.runtime = AgentRuntime(gateway=_GatewayShim(MockLLM()), tools=ToolExecutor())
        if "llm" in self.mocks:
            self.runtime.gateway = _GatewayShim(self.mocks["llm"])
        if "tools" in self.mocks:
            for name, tool in self.mocks["tools"].items():
                self.runtime.tools.register(_make_tool(name, tool))
        return await self.runtime.run(self._spec, message, tenant_id=tenant_id, **kw)


def _make_tool(name: str, mock: MockTool) -> Callable[..., Any]:
    async def _fn(**kwargs: Any) -> Any:
        return await mock(**kwargs)
    _fn.__name__ = name
    _fn.__agentforge_tool__ = True  # type: ignore[attr-defined]
    _fn.__agentforge_spec__ = _tool_spec(name)  # type: ignore[attr-defined]
    return _fn


def _tool_spec(name: str):
    from agentforge.models.config import CircuitBreakerConfig, RateLimitConfig, RetryConfig
    from agentforge.tool import ToolSpec
    return ToolSpec(
        name=name, description="mock", permissions=[], rate_limit=RateLimitConfig(),
        timeout=30, retry_policy=RetryConfig(), circuit_breaker=CircuitBreakerConfig(),
        execution_type="function", endpoint=None, fn=lambda: None,
    )


class _GatewayShim:
    def __init__(self, llm: MockLLM) -> None:
        self._llm = llm

    async def chat(self, request: LLMRequest) -> LLMResponse:
        return await self._llm.chat(request)

    async def embed(self, request: Any) -> Any:
        raise NotImplementedError
