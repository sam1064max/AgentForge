# SPDX-License-Identifier: Apache-2.0
"""Tests for the @Agent decorator and runtime execution."""

from __future__ import annotations

import asyncio

import pytest

from agentforge.agent import Agent, AgentBase, AgentSpec
from agentforge.models.config import ModelConfig
from agentforge.models.llm import Message, ToolCall
from agentforge.runtime.execution import AgentRuntime, ToolExecutor
from agentforge.testing.harness import MockLLM, MockTool


def _make_agent(name: str = "echo-agent") -> type:
    @Agent(name=name, description="echo", model=ModelConfig(provider="mock", model="model"))
    class EchoAgent:
        @Agent.system_prompt
        def system(self) -> str:
            return "You are a helpful assistant."

        @Agent.on_message
        async def handle(self, message: str) -> None:
            resp = await self.ctx.generate()
            self.ctx.metadata["last_llm_response"] = resp
            self.ctx.metadata["final_answer"] = resp.message.content

    return EchoAgent


def test_agent_spec_collected():
    cls = _make_agent()
    spec = cls.__agentforge_spec__
    assert isinstance(spec, AgentSpec)
    assert spec.name == "echo-agent"
    assert "on_message" in spec.hooks
    assert "system_prompt" in spec.hooks


def test_agent_runs_end_to_end():
    cls = _make_agent()
    spec = cls.__agentforge_spec__
    runtime = AgentRuntime(
        gateway=_Shim(MockLLM(responses=["Hello there!"])),
        tools=ToolExecutor(),
    )

    async def run():
        return await runtime.run(spec, "hi")

    result = asyncio.run(run())
    assert result.status == "completed"
    assert result.output == "Hello there!"
    assert result.llm_calls == 1


def test_agent_tool_loop():
    cls = _make_agent()
    spec = cls.__agentforge_spec__

    captured = {}

    @Agent.on_message
    async def handle(self, message: str) -> None:
        resp = await self.ctx.generate(
            tools=[{"name": "get_weather", "description": "weather", "parameters": {"type": "object", "properties": {}}, "required": []}]
        )
        captured["tool_calls"] = resp.tool_calls
        self.ctx.metadata["last_llm_response"] = resp
        if resp.tool_calls:
            for tc in resp.tool_calls:
                res = await self.tools.execute(tool=tc.name, args=tc.arguments, context={})
                captured.setdefault("results", []).append(res.output)
                self.ctx.metadata.setdefault("history", []).append(
                    Message(role="tool", content=str(res.output), tool_call_id=tc.id, name=tc.name)
                )
            resp2 = await self.ctx.generate()
            self.ctx.metadata["last_llm_response"] = resp2
            self.ctx.metadata["final_answer"] = resp2.message.content

    cls.__agentforge_spec__.hooks["on_message"] = handle

    mock_tool = MockTool(return_value={"temp": 72})
    tools = ToolExecutor()
    tools.register(_make_tool("get_weather", mock_tool))

    runtime = AgentRuntime(
        gateway=_Shim(MockLLM(tool_calls=[ToolCall(id="c1", name="get_weather", arguments={"city": "NYC"})], responses=["It is 72F."])),
        tools=tools,
    )

    async def run():
        return await runtime.run(spec, "weather?")

    result = asyncio.run(run())
    assert result.status == "completed"
    assert result.output == "It is 72F."
    assert ("get_weather", {"city": "NYC"}) in result.tool_calls


def _Shim(llm: MockLLM):
    class _G:
        async def chat(self, request):
            return await llm.chat(request)

        async def embed(self, request):
            raise NotImplementedError

    return _G()


def _make_tool(name: str, mock: MockTool):
    async def _fn(**kwargs):
        return await mock(**kwargs)

    _fn.__name__ = name
    _fn.__agentforge_tool__ = True
    from agentforge.models.config import CircuitBreakerConfig, RateLimitConfig, RetryConfig
    from agentforge.tool import ToolSpec

    _fn.__agentforge_spec__ = ToolSpec(
        name=name, description="mock", permissions=[], rate_limit=RateLimitConfig(),
        timeout=30, retry_policy=RetryConfig(), circuit_breaker=CircuitBreakerConfig(),
        execution_type="function", endpoint=None, fn=_fn,
    )
    return _fn
