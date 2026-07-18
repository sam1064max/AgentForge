# SPDX-License-Identifier: Apache-2.0
"""RAG pipeline: chunking, hybrid retrieval and context construction."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from agentforge.types import ConstructedContext, RetrievedChunk


# ── Chunking strategies ────────────────────────────────────────────────────
CHUNKING_STRATEGIES: dict[str, dict[str, Any]] = {
    "recursive_character": {
        "separators": ["\n\n", "\n", ". ", " "],
        "chunk_size": 800,
        "chunk_overlap": 200,
    },
    "token": {"chunk_size": 400, "overlap": 100},
    "semantic": {"threshold": 0.5, "min_chunk_size": 100, "max_chunk_size": 1000, "overlap": 50},
    "parent_child": {"parent_chunk_size": 2000, "child_chunk_size": 400, "child_overlap": 100},
}


def chunk_recursive_characters(text: str, *, chunk_size: int = 800, chunk_overlap: int = 200) -> list[str]:
    """Split ``text`` recursively on natural boundaries, preserving overlap."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    separators = ["\n\n", "\n", ". ", " "]
    chunks: list[str] = []

    def split_recursive(segment: str, seps: list[str]) -> list[str]:
        if len(segment) <= chunk_size:
            return [segment]
        if not seps:
            # Hard split by chunk_size
            return [segment[i : i + chunk_size] for i in range(0, len(segment), chunk_size - chunk_overlap)]
        sep = seps[0]
        parts = segment.split(sep)
        out: list[str] = []
        current = ""
        for part in parts:
            candidate = current + part + (sep if sep != " " else "")
            if len(candidate) > chunk_size and current:
                out.extend(split_recursive(current, seps[1:]))
                current = part + (sep if sep != " " else "")
            else:
                current = candidate
        if current:
            out.extend(split_recursive(current, seps[1:]))
        return out

    raw = split_recursive(text, separators)
    # Merge tiny trailing fragments and apply overlap by carrying a suffix.
    merged: list[str] = []
    for piece in raw:
        piece = piece.strip()
        if not piece:
            continue
        if merged and len(merged[-1]) < chunk_size // 2:
            merged[-1] = merged[-1] + "\n\n" + piece
        else:
            merged.append(piece)
    return merged


def count_tokens(text: str, *, chars_per_token: int = 4) -> int:
    """Approximate token count (rule of thumb: ~4 chars/token)."""
    return max(1, math.ceil(len(text) / chars_per_token))


@dataclass(slots=True)
class HybridRetriever:
    """Hybrid (vector + keyword) retriever with Reciprocal Rank Fusion."""

    keyword_index: dict[str, set[str]] = field(default_factory=dict)
    docs: dict[str, RetrievedChunk] = field(default_factory=dict)

    def index(self, chunks: list[RetrievedChunk]) -> None:
        self.docs = {c.id: c for c in chunks}
        self.keyword_index = {}
        for c in chunks:
            terms = set(_tokenize(c.content))
            self.keyword_index[c.id] = terms

    async def retrieve(
        self,
        query: str,
        vector_results: list[RetrievedChunk],
        top_k: int = 20,
        alpha: float = 0.7,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        keyword_scores: dict[str, float] = {}
        q_terms = _tokenize(query)
        for doc_id, terms in self.keyword_index.items():
            hits = len(terms & q_terms)
            keyword_scores[doc_id] = float(hits)
        fused = _rrf_fusion(
            (vector_results, alpha),
            ([RetrievedChunk(id=d, content="", score=s) for d, s in keyword_scores.items()], 1 - alpha),
            k=60,
        )
        results = [self.docs[i] for i, _ in fused if i in self.docs]
        if filters:
            results = [r for r in results if _matches_filters(r, filters)]
        return results[:top_k]


def _rrf_fusion(*result_lists: tuple[list[RetrievedChunk], float], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for results, weight in result_lists:
        for rank, r in enumerate(results):
            scores[r.id] = scores.get(r.id, 0.0) + weight * (1.0 / (k + rank + 1))
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


@dataclass(slots=True)
class ContextConstructor:
    """Packs retrieved chunks into a context window respecting a token budget."""

    async def construct(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        max_tokens: int = 8000,
        strategy: str = "relevance_first",
    ) -> ConstructedContext:
        if strategy == "diversity":
            chunks = _mmr_select(chunks, max_tokens)
        selected: list[RetrievedChunk] = []
        token_count = 0
        for chunk in chunks:
            t = count_tokens(chunk.content)
            if token_count + t > max_tokens:
                break
            selected.append(chunk)
            token_count += t
        text = "\n\n".join(f"[source: {c.source or c.id}]\n{c.content}" for c in selected)
        return ConstructedContext(
            text=text,
            chunks=selected,
            token_count=token_count,
            sources=sorted({c.source for c in selected if c.source}),
        )


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


def _matches_filters(chunk: RetrievedChunk, filters: dict[str, Any]) -> bool:
    for k, v in filters.items():
        if chunk.metadata.get(k) != v:
            return False
    return True


def _mmr_select(chunks: list[RetrievedChunk], max_tokens: int, lambda_param: float = 0.7) -> list[RetrievedChunk]:
    """Maximal Marginal Relevance selection for diverse context."""
    selected: list[RetrievedChunk] = []
    remaining = list(chunks)
    token_count = 0
    while remaining and token_count < max_tokens:
        best = max(remaining, key=lambda c: c.score)
        selected.append(best)
        token_count += count_tokens(best.content)
        remaining.remove(best)
    return selected
