# SPDX-License-Identifier: Apache-2.0
"""Knowledge base interfaces and connectors.

The knowledge layer ingests documents from pluggable connectors, chunks them,
embeds them, and serves them to the RAG service. The :class:`KnowledgeBase`
facade mirrors the architecture's connector framework (Confluence, S3, GitHub,
web crawler, …) with local-friendly defaults.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from agentforge.interfaces import KnowledgeStore


@dataclass(slots=True)
class DocumentMetadata:
    doc_id: str
    title: str
    source_type: str
    content_type: str = "text/plain"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RawDocument:
    doc_id: str
    title: str
    content: str
    content_type: str = "text/plain"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Chunk:
    chunk_index: int
    content: str
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class KnowledgeConnector(abc.ABC):
    """Base class for knowledge source connectors."""

    source_type: str = "unknown"

    @abc.abstractmethod
    async def discover(self) -> list[DocumentMetadata]:
        """Discover available documents from the source."""

    @abc.abstractmethod
    async def fetch(self, doc_id: str) -> RawDocument:
        """Fetch a specific document by id."""

    async def watch(self) -> AsyncIterator[Any]:
        """Optional change stream. Default: never emits."""
        return
        yield  # pragma: no cover - makes this an async generator


class LocalFileConnector(KnowledgeConnector):
    """Connector that reads a directory of text/markdown files."""

    source_type = "local"

    def __init__(self, root: str) -> None:
        self.root = root

    async def discover(self) -> list[DocumentMetadata]:
        from pathlib import Path

        files: list[DocumentMetadata] = []
        base = Path(self.root)
        if not base.exists():
            return files
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in {".md", ".txt", ".py", ".json"}:
                files.append(DocumentMetadata(
                    doc_id=str(path.relative_to(base)),
                    title=path.stem,
                    source_type=self.source_type,
                    content_type="text/markdown" if path.suffix == ".md" else "text/plain",
                ))
        return files

    async def fetch(self, doc_id: str) -> RawDocument:
        from pathlib import Path

        path = Path(self.root) / doc_id
        content = path.read_text(encoding="utf-8")
        return RawDocument(
            doc_id=doc_id,
            title=path.stem,
            content=content,
            content_type="text/markdown" if path.suffix == ".md" else "text/plain",
        )


class KnowledgeBase:
    """Facade that ingests documents and serves chunks via a store."""

    def __init__(self, store: KnowledgeStore, *, embedder: Any = None) -> None:
        self._store = store
        self._embedder = embedder
        self._connectors: dict[str, KnowledgeConnector] = {}

    def register_connector(self, name: str, connector: KnowledgeConnector) -> None:
        self._connectors[name] = connector

    async def ingest_file(self, *, source: str, title: str, content: str, chunk_size: int = 800) -> str:
        chunks = chunk_recursive_characters(content, chunk_size=chunk_size)
        payload = []
        for i, chunk in enumerate(chunks):
            vector = None
            if self._embedder is not None:
                vector = (await self._embedder.embed([chunk], "openai/text-embedding-3-small"))[0]
            payload.append({"id": f"{title}-{i}", "vector": vector, "content": chunk, "metadata": {"title": title, "index": i}})
        return await self._store.add_document(source=source, title=title, chunks=payload)

    async def search(self, *, query_vector: list[float], top_k: int = 10, **filters: Any) -> list[dict[str, Any]]:
        return await self._store.search(query_vector=query_vector, top_k=top_k, **filters)
