# SPDX-License-Identifier: Apache-2.0
"""Example: a simple order-status agent using the AgentForge SDK.

Run with:
    python examples/order_agent.py

Uses the local in-memory backend and a scripted mock model gateway so the
example runs with zero external services.
"""

from __future__ import annotations

import asyncio

from agentforge.agent import Agent
from agentforge.models.config import ModelConfig
from agentforge.models.llm import Message, ToolCall
from agentforge.runtime.execution import AgentRuntime, ToolExecutor
from agentforge.testing.harness import MockLLM
from agentforge.tool import Tool


# --- Tools -----------------------------------------------------------------
_ORDERS = {
    "ORD-123": {"status": "shipped", "eta": "2026-07-21", "carrier": "UPS"},
    "ORD-456": {"status": "processing", "eta": "2026-07-25", "carrier": "FedEx"},
}


@Tool(name="lookup_order", description="Look up an order by id", permissions=["orders:read"])
async def lookup_order(order_id: str) -> dict:
    """Look up an order.

    :param order_id: The order identifier, e.g. ORD-123.
    """
    return _ORDERS.get(order_id, {"error": "not found"})


@Tool(name="cancel_order", description="Cancel an order", permissions=["orders:write"])
async def cancel_order(order_id: str) -> dict:
    """Cancel an order.

    :param order_id: The order identifier to cancel.
    """
    return {"cancelled": order_id}


# --- Agent -----------------------------------------------------------------
@Agent(
    name="order-agent",
    description="Answers questions about order status and can cancel orders.",
    model=ModelConfig(provider="mock", model="model"),
    tools=["lookup_order", "cancel_order"],
    guardrails=["pii-detection", "prompt-injection"],
)
class OrderAgent:
    @Agent.system_prompt
    def system(self) -> str:
        return "You are a customer-support agent for order inquiries."

    @Agent.on_message
    async def handle(self, message: str) -> None:
        resp = await self.ctx.generate(
            tools=[
                {
                    "name": "lookup_order",
                    "description": "Look up an order by id",
                    "parameters": {
                        "type": "object",
                        "properties": {"order_id": {"type": "string"}},
                    },
                    "required": ["order_id"],
                }
            ]
        )
        self.ctx.metadata["last_llm_response"] = resp
        if resp.tool_calls:
            for tc in resp.tool_calls:
                result = await self.ctx.tools.execute(
                    tool=tc.name, args=tc.arguments, context={"agent_id": "order-agent"}
                )
                self.ctx.metadata.setdefault("tool_results", []).append({tc.name: result.output})
                self.ctx.metadata.setdefault("history", []).append(
                    Message(role="tool", content=str(result.output), tool_call_id=tc.id, name=tc.name)
                )
            resp2 = await self.ctx.generate()
            self.ctx.metadata["last_llm_response"] = resp2
            self.ctx.metadata["final_answer"] = resp2.message.content
        elif resp.message.content:
            self.ctx.metadata["final_answer"] = resp.message.content


def _main() -> None:
    tools = ToolExecutor()
    tools.register(lookup_order)
    tools.register(cancel_order)

    scripted = MockLLM(
        tool_calls=[ToolCall(id="t1", name="lookup_order", arguments={"order_id": "ORD-123"})],
        responses=["Your order ORD-123 has shipped and arrives 2026-07-21 via UPS."],
    )

    class _Gateway:
        async def chat(self, request):
            return await scripted.chat(request)

        async def embed(self, request):
            raise NotImplementedError

    runtime = AgentRuntime(gateway=_Gateway(), tools=tools)

    async def run() -> None:
        result = await runtime.run(OrderAgent.__agentforge_spec__, "What is the status of ORD-123?")
        print("status:", result.status)
        print("output:", result.output)
        print("tool_calls:", result.tool_calls)
        print("llm_calls:", result.llm_calls)

    asyncio.run(run())


if __name__ == "__main__":
    _main()
