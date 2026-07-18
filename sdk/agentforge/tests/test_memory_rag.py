# SPDX-License-Identifier: Apache-2.0
"""Tests for memory provider and RAG pipeline."""

from __future__ import annotations

import asyncio

from agentforge.knowledge.rag import (
    ContextConstructor,
    HybridRetriever,
    chunk_recursive_characters,
    count_tokens,
)
from agentforge.memory.in_memory import InMemoryMemoryProvider
from agentforge.types import RetrievedChunk


def test_memory_store_and_recall():
    mem = InMemoryMemoryProvider()

    async def run():
        mid = await mem.store(scope="tenant-a", key="k1", value={"v": 1}, kind="fact")
        items = await mem.recall(scope="tenant-a", query="anything")
        conv = await mem.start_conversation(scope="tenant-a", user_id="u1")
        await mem.add_turn(conversation_id=conv, role="user", content="hi")
        c = await mem.get_conversation(conv)
        return mid, items, c

    mid, items, conv = asyncio.run(run())
    assert mid.startswith("mem-")
    assert any(i["id"] == mid for i in items)
    assert conv["turns"][0]["content"] == "hi"


def test_memory_filters():
    mem = InMemoryMemoryProvider()

    async def run():
        await mem.store(scope="s", key="a", value=1, kind="fact")
        await mem.store(scope="s", key="b", value=2, kind="rule")
        return await mem.recall(scope="s", query="", kind="rule")

    items = asyncio.run(run())
    assert len(items) == 1
    assert items[0]["key"] == "b"


def test_recursive_chunking():
    text = "First sentence here. " + "Second sentence. " * 50
    chunks = chunk_recursive_characters(text, chunk_size=120, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)


def test_count_tokens():
    assert count_tokens("abcd", chars_per_token=4) == 1


def test_hybrid_retriever_and_context():
    chunks = [
        RetrievedChunk(id="c1", content="the cat sat on the mat", score=0.9, source="doc1"),
        RetrievedChunk(id="c2", content="a dog ran in the park", score=0.4, source="doc2"),
    ]
    retriever = HybridRetriever()
    retriever.index(chunks)

    async def run():
        vector_results = [RetrievedChunk(id="c1", content="", score=0.9)]
        fused = await retriever.retrieve("cat mat", vector_results=vector_results, top_k=5)
        ctx = await ContextConstructor().construct("cat mat", fused, max_tokens=1000)
        return fused, ctx

    fused, ctx = asyncio.run(run())
    assert fused[0].id == "c1"
    assert "cat sat on the mat" in ctx.text
    assert "doc1" in ctx.sources
