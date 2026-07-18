"""In-process memory backend.

Provides short-term (conversation), long-term (KV), and semantic (vector)
memory backed by local data structures. This is the default memory backend for
the SDK's :class:`~agentforge.runtime.local.LocalBackend`, so agents run without
any external database. Production deployments swap this for the Memory Service.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Any

from agentforge.logging import get_logger

logger = get_logger(__name__)


class BaseMemory(ABC):
    """Abstract memory store."""

    @abstractmethod
    def put(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def keys(self) -> list[str]: ...


class ConversationMemory(BaseMemory):
    """Short-term, ordered conversation history scoped to a session."""

    def __init__(self, *, agent_id: str | None = None, session_id: str | None = None,
                 max_turns: int = 100) -> None:
        self.agent_id = agent_id
        self.session_id = session_id
        self.max_turns = max_turns
        self._store: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.RLock()

    def _key(self) -> str:
        return f"{self.agent_id or 'agent'}:{self.session_id or 'default'}"

    def append(self, message: dict[str, Any]) -> None:
        with self._lock:
            hist = self._store.setdefault(self._key(), [])
            hist.append(message)
            if self.max_turns and len(hist) > self.max_turns * 2:
                del hist[: len(hist) - self.max_turns * 2]

    def history(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._store.get(self._key(), []))

    # BaseMemory interface (session-scoped KV)
    def put(self, key: str, value: Any) -> None:
        self.append({"role": "system", "content": f"{key}: {value}"})

    def get(self, key: str, default: Any = None) -> Any:
        for m in reversed(self.history()):
            if m.get("content", "").startswith(f"{key}: "):
                return m["content"][len(key) + 2:]
        return default

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(self._key(), None)

    def keys(self) -> list[str]:
        return [self._key()]


class KVStore(BaseMemory):
    """Long-term key/value memory."""

    def __init__(self, namespace: str = "default") -> None:
        self.namespace = namespace
        self._store: dict[str, Any] = {}
        self._lock = threading.RLock()

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[f"{self.namespace}:{key}"] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._store.get(f"{self.namespace}:{key}", default)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(f"{self.namespace}:{key}", None)

    def keys(self) -> list[str]:
        prefix = f"{self.namespace}:"
        return [k[len(prefix):] for k in self._store if k.startswith(prefix)]


class SemanticMemory(BaseMemory):
    """Lightweight in-process semantic (vector) memory using cosine similarity.

    Embeddings are produced by a pluggable function (default: a deterministic
    hashing-based pseudo-embedding so the SDK works with zero dependencies).
    """

    def __init__(self, *, dimensions: int = 256, embed_fn: Any = None) -> None:
        self.dimensions = dimensions
        self._embed_fn = embed_fn or _hash_embedding
        self._vectors: dict[str, list[float]] = {}
        self._meta: dict[str, Any] = {}
        self._lock = threading.RLock()

    def put(self, key: str, value: Any, metadata: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._vectors[key] = self._embed_fn(_as_text(value))
            self._meta[key] = {"value": value, "metadata": metadata or {}}

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            entry = self._meta.get(key)
            return entry["value"] if entry else default

    def delete(self, key: str) -> None:
        with self._lock:
            self._vectors.pop(key, None)
            self._meta.pop(key, None)

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._vectors.keys())

    def similarity_search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        q = self._embed_fn(query)
        with self._lock:
            scored = [
                (key, _cosine(q, vec)) for key, vec in self._vectors.items()
            ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {"key": key, "score": score, **self._meta[key]}
            for key, score in scored[:top_k]
        ]


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        import json as _json
        return _json.dumps(value, default=str)
    except Exception:
        return str(value)


def _hash_embedding(text: str, dimensions: int = 256) -> list[float]:
    """Deterministic, dependency-free pseudo-embedding for local dev/tests."""
    vec = [0.0] * dimensions
    for i, ch in enumerate(text.encode("utf-8")):
        vec[(ch + i) % dimensions] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
