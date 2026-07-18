# SPDX-License-Identifier: Apache-2.0
"""Model gateway: unified LLM + embedding access.

Provides the :class:`ModelGateway` interface plus a local implementation with a
pluggable provider adapter. A :class:`MockProvider` is included for tests and
offline development (no network/API keys required). Real providers (OpenAI,
Anthropic, …) are loaded lazily so the SDK has zero hard third-party deps.
"""

from __future__ import annotations

import abc
import json
import time
from dataclasses import dataclass, field
from typing import Any

from agentforge.errors import ModelGatewayError
from agentforge.models.llm import (
    EmbeddingRequest,
    EmbeddingResponse,
    LLMRequest,
    LLMResponse,
    Message,
    ToolCall,
)
from agentforge.models.embeddings import Embedder


class LLMProvider(abc.ABC):
    """Adapter for a single LLM vendor."""

    name: str

    @abc.abstractmethod
    async def chat(self, request: LLMRequest) -> LLMResponse: ...

    @abc.abstractmethod
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse: ...


@dataclass(slots=True)
class _EmbeddingResult:
    vectors: list[list[float]]
    model: str
    dimensions: int
    cost: float


class MockProvider(LLMProvider):
    """Deterministic, network-free provider for tests and local dev.

    Echoes a plausible response derived from the last user message and supports a
    tiny scripted tool-call mode so the runtime can be exercised end-to-end.
    """

    name = "mock"

    def __init__(self, *, latency_ms: int = 5, model: str = "mock/model") -> None:
        self.latency_ms = latency_ms
        self.model = model

    async def chat(self, request: LLMRequest) -> LLMResponse:
        time.sleep(self.latency_ms / 1000.0)
        user_msg = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
        response_text = f"[mock] Response to: {user_msg[:120]}"
        tool_calls: list[ToolCall] = []
        if request.tools:
            # Deterministically call the first tool with a sample arg to exercise the loop.
            t = request.tools[0]
            arg = (t.required[0] if t.required else "input")
            tool_calls.append(ToolCall(id="call_1", name=t.name, arguments={arg: user_msg[:40]}))
            response_text = ""
        return LLMResponse(
            message=Message(role="assistant", content=response_text, tool_calls=tool_calls or None),
            tool_calls=tool_calls,
            model=self.model,
            provider=self.name,
            tokens_input=max(1, len(json.dumps([m.content for m in request.messages])) // 4),
            tokens_output=max(1, len(response_text) // 4),
            cost=0.0,
            latency_ms=self.latency_ms,
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        # Deterministic pseudo-embedding: hashed bag-of-words in 32 dims.
        import hashlib

        dim = 32
        vectors: list[list[float]] = []
        for text in request.texts:
            vec = [0.0] * dim
            for i, tok in enumerate(text.lower().split()):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                vec[h % dim] += 1.0
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            vectors.append([v / norm for v in vec])
        return EmbeddingResponse(vectors=vectors, model=self.model, dimensions=dim)

    def as_embedder(self) -> Embedder:
        provider = self

        class _Emb(Embedder):
            async def embed(self, texts: list[str], model: str) -> list[list[float]]:
                return (await provider.embed(EmbeddingRequest(texts=texts, model=model))).vectors

        return _Emb()


class ModelGateway:
    """Unified gateway that routes requests to a provider by model prefix."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._default: LLMProvider | None = None

    def register_provider(self, provider: LLMProvider, *, default: bool = False) -> None:
        self._providers[provider.name] = provider
        if default or self._default is None:
            self._default = provider

    def _resolve(self, model: str) -> LLMProvider:
        prefix = model.split("/", 1)[0]
        provider = self._providers.get(prefix) or self._default
        if provider is None:
            raise ModelGatewayError(f"No provider registered for model '{model}'")
        return provider

    async def chat(self, request: LLMRequest) -> LLMResponse:
        return await self._resolve(request.model).chat(request)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return await self._resolve(request.model).embed(request)

    async def list_models(self) -> list[str]:
        return [p.name for p in self._providers.values()]
