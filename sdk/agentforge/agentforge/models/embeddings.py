# SPDX-License-Identifier: Apache-2.0
"""Embedding client abstraction and model registry helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class EmbeddingModel:
    """Metadata for an embedding model."""

    id: str
    provider: str
    name: str
    dimensions: int
    input_price_per_1k: float = 0.0
    status: str = "approved"


class Embedder(Protocol):
    """Protocol implemented by embedding backends."""

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        """Return a vector for each input text."""
        ...


@dataclass(slots=True)
class TokenEstimate:
    """Estimated token count for a piece of text."""

    text: str
    tokens: int
    model: str = "gpt-4o"
