# SPDX-License-Identifier: Apache-2.0
"""In-memory memory provider used for local development and tests.

The :class:`InMemoryMemoryProvider` is a fully functional implementation of the
:class:`~agentforge.interfaces.MemoryProvider` interface backed by Python data
structures. Production deployments substitute the PostgreSQL + Qdrant backed
provider (see ``services/memory``) without any change to agent code.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Any

from agentforge.interfaces import MemoryProvider
from agentforge.models.embeddings import Embedder


class InMemoryMemoryProvider(MemoryProvider):
    """Conversation, short-term and semantic memory backed by dicts."""

    def __init__(self, *, embedder: Embedder | None = None) -> None:
        self._embedder = embedder
        self._items: dict[str, dict[str, Any]] = {}
        self._by_scope: dict[str, list[str]] = defaultdict(list)
        self._conversations: dict[str, dict[str, Any]] = {}

    async def store(self, *, scope: str, key: str, value: Any, **meta: Any) -> str:
        memory_id = meta.pop("memory_id", None) or f"mem-{uuid.uuid4().hex[:12]}"
        self._items[memory_id] = {
            "id": memory_id,
            "scope": scope,
            "key": key,
            "value": value,
            "created_at": time.time(),
            "access_count": 0,
            **meta,
        }
        self._by_scope[scope].append(memory_id)
        return memory_id

    async def recall(self, *, scope: str, query: str, top_k: int = 5, **filters: Any) -> list[dict[str, Any]]:
        candidates = [self._items[i] for i in self._by_scope.get(scope, [])]
        if filters:
            candidates = [c for c in candidates if _matches(c, filters)]
        # Rank by simple lexical overlap when no embedder is present.
        if self._embedder is not None and candidates:
            q_vec = (await self._embedder.embed([query], "openai/text-embedding-3-small"))[0]
            for c in candidates:
                c_vec = c.get("vector")
                if c_vec:
                    c["_score"] = _cosine(q_vec, c_vec)
            candidates.sort(key=lambda c: c.get("_score", 0.0), reverse=True)
        for c in candidates[:top_k]:
            c["access_count"] = c.get("access_count", 0) + 1
        return [{k: v for k, v in c.items() if not k.startswith("_")} for c in candidates[:top_k]]

    async def search(self, *, scope: str, vector: list[float], top_k: int = 5, **filters: Any) -> list[dict[str, Any]]:
        candidates = [self._items[i] for i in self._by_scope.get(scope, [])]
        if filters:
            candidates = [c for c in candidates if _matches(c, filters)]
        for c in candidates:
            c_vec = c.get("vector")
            c["_score"] = _cosine(vector, c_vec) if c_vec else 0.0
        candidates.sort(key=lambda c: c.get("_score", 0.0), reverse=True)
        return [{k: v for k, v in c.items() if not k.startswith("_")} for c in candidates[:top_k]]

    async def delete(self, memory_id: str) -> None:
        item = self._items.pop(memory_id, None)
        if item:
            ids = self._by_scope.get(item["scope"], [])
            if memory_id in ids:
                ids.remove(memory_id)

    # Conversation helpers -------------------------------------------------
    async def start_conversation(self, *, scope: str, user_id: str | None = None) -> str:
        conv_id = f"conv-{uuid.uuid4().hex[:12]}"
        self._conversations[conv_id] = {
            "id": conv_id,
            "scope": scope,
            "user_id": user_id,
            "turns": [],
            "summary": None,
        }
        return conv_id

    async def add_turn(self, *, conversation_id: str, role: str, content: str, **meta: Any) -> dict[str, Any]:
        conv = self._conversations[conversation_id]
        turn = {"sequence": len(conv["turns"]) + 1, "role": role, "content": content, **meta}
        conv["turns"].append(turn)
        return turn

    async def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        return self._conversations[conversation_id]


def _matches(item: dict[str, Any], filters: dict[str, Any]) -> bool:
    for k, v in filters.items():
        if item.get(k) != v:
            return False
    return True


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
