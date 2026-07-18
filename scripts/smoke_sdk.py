"""Smoke test for the AgentForge SDK local runtime path."""

import sys

sys.path.insert(0, "sdk")

from agentforge import Agent, Tool, ModelConfig
from agentforge.models import FunctionCall, ToolCall
from agentforge.runtime import AgentContext


@Tool(name="add", description="Add two numbers")
def add(a: int, b: int) -> int:
    return a + b


@Agent(
    name="calc",
    version="1.0.0",
    model=ModelConfig(provider="mock", model="mock"),
    tools=["add"],
)
class Calc:
    def __init__(self, ctx: AgentContext) -> None:
        self.ctx = ctx

    @Agent.on_message
    async def handle(self, message: str) -> str:
        res = await self.ctx.backend.execute_tool(
            ToolCall(id="c1", function=FunctionCall(name="add", arguments='{"a": 2, "b": 3}'))
        )
        return res.content


def main() -> None:
    r = Calc.run("hello")
    print("status:", r.status)
    print("output:", r.output)
    print("trace_id:", r.trace_id)
    print("latency_ms:", r.latency_ms)
    assert r.status == "completed"
    assert r.output == "5"
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
