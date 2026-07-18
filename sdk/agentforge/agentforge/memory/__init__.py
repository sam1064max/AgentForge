# SPDX-License-Identifier: Apache-2.0
"""Memory package public API.

Exposes the memory tiers described in the architecture (short-term, long-term,
semantic, shared) through a single facade, :class:`Memory`, which delegates to a
pluggable :class:`~agentforge.interfaces.MemoryProvider`.
"""

from __future__ import annotations

from typing import Any

from agentforge.interfaces import MemoryProvider
from agentforge.memory.in_memory import InMemoryMemoryProvider


class Memory:
    """High-level memory facade offered to agents via ``ctx.memory``."""

    def __init__(self, provider: MemoryProvider | None = None, *, tenant_id: str = "default") -> None:
        self._provider = provider or InMemoryMemoryProvider()
        self._tenant_id = tenant_id

    async def recall(self, *, query: str, sources: list[str] | None = None, top_k: int = 5, **filters: Any) -> list[dict[str, Any]]:
        scope = _scope(self._tenant_id, sources[0] if sources else "semantic")
        return await self._provider.recall(scope=scope, query=query, top_k=top_k, **filters)

    async def store(self, value: Any, *, scope: str = "semantic", key: str | None = None, **meta: Any) -> str:
        return await self._provider.store(
            scope=_scope(self._tenant_id, scope), key=key or "item", value=value, **meta
        )

    async def search(self, *, vector: list[float], top_k: int = 5, scope: str = "semantic", **filters: Any) -> list[dict[str, Any]]:
        return await self._provider.search(scope=_scope(self._tenant_id, scope), vector=vector, top_k=top_k, **filters)

    async def delete(self, memory_id: str) -> None:
        await self._provider.delete(memory_id)


def _scope(tenant_id: str, tier: str) -> str:
    return f"{tenant_id}:{tier}"
