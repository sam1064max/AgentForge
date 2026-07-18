# SPDX-License-Identifier: Apache-2.0
"""Example: a retrieval-augmented (RAG) pipeline using the AgentForge SDK.

Run with:
    python examples/rag_agent.py

Demonstrates chunking, hybrid retrieval and context construction against the
in-memory knowledge store with a scripted mock model gateway.
"""

from __future__ import annotations

import asyncio

from agentforge.knowledge.base import KnowledgeConnector, RawDocument, DocumentMetadata
from agentforge.knowledge.rag import (
    ContextConstructor,
    HybridRetriever,
    chunk_recursive_characters,
)
from agentforge.types import RetrievedChunk


_DOC = """
AgentForge is an enterprise platform for building, deploying and governing AI agents.
Agents are declarative units composed of a model, tools, memory and guardrails.
The control plane deploys agents to isolated tenant workspaces.
Memory is tiered into short-term, long-term, semantic and shared scopes.
Observability captures every LLM call, tool call and guardrail decision.
"""


class StaticKnowledgeConnector(KnowledgeConnector):
    """In-memory connector backed by a fixed document."""

    source_type = "static"

    async def discover(self) -> list[DocumentMetadata]:
        return [DocumentMetadata(doc_id="agentforge-overview", title="AgentForge Overview", source_type=self.source_type)]

    async def fetch(self, doc_id: str) -> RawDocument:
        return RawDocument(
            doc_id=doc_id,
            title="AgentForge Overview",
            content=_DOC,
            content_type="text/plain",
        )


def _main() -> None:
    # 1. Chunk the document.
    chunks_text = chunk_recursive_characters(_DOC, chunk_size=160, chunk_overlap=20)
    chunks = [
        RetrievedChunk(id=f"chunk-{i}", content=c, source="agentforge-overview", score=0.0)
        for i, c in enumerate(chunks_text)
    ]

    # 2. Build a hybrid retriever and index the chunks.
    retriever = HybridRetriever()
    retriever.index(chunks)

    async def run() -> None:
        vector_results = [RetrievedChunk(id=chunks[2].id, content="", score=0.9)]
        retrieved = await retriever.retrieve(
            "how is memory organised?", vector_results=vector_results, top_k=3
        )
        context = await ContextConstructor().construct("how is memory organised?", retrieved, max_tokens=2000)
        print("Retrieved chunks:", len(retrieved))
        print("Context token estimate:", context.token_count)
        print("Sources:", context.sources)
        print("---- constructed context ----")
        print(context.text[:400])

    asyncio.run(run())


if __name__ == "__main__":
    _main()
