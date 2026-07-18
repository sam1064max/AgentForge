# SPDX-License-Identifier: Apache-2.0
"""Tests for the @Tool decorator and JSON-schema generation."""

from __future__ import annotations

import pytest

from agentforge.tool import Tool, get_tool_spec, is_tool


def test_tool_registers_metadata():
    @Tool(name="lookup_order", description="Look up an order", permissions=["orders:read"])
    async def lookup(order_id: str, verbose: bool = False) -> dict:
        """Look up an order.

        :param order_id: The order id to fetch.
        """
        return {"order_id": order_id, "verbose": verbose}

    assert is_tool(lookup)
    spec = get_tool_spec(lookup)
    assert spec.name == "lookup_order"
    assert spec.permissions == ["orders:read"]
    assert "order_id" in spec.schema["properties"]
    assert spec.schema["required"] == ["order_id"]
    assert spec.schema["properties"]["verbose"]["type"] == "boolean"


def test_tool_invocation_async():
    @Tool(name="add", description="add two numbers")
    async def add(a: int, b: int) -> int:
        return a + b

    async def run():
        return await add(a=2, b=3)

    import asyncio

    assert asyncio.run(run()) == 5


def test_tool_invocation_sync():
    @Tool(name="concat", description="concat")
    def concat(a: str, b: str) -> str:
        return a + b

    import asyncio

    assert asyncio.run(concat("x", b="y")) == "xy"


def test_rate_limit_parsing():
    @Tool(name="t", rate_limit="120/min")
    def t() -> int:
        return 1

    assert get_tool_spec(t).rate_limit.requests_per_minute == 120
