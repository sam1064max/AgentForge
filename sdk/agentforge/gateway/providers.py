"""LLM provider adapters for the Model Gateway.

Each adapter normalizes a provider's API to the unified
:class:`~agentforge.gateway.LLMRequest` / :class:`~agentforge.gateway.LLMResponse`
contract. The :class:`ProviderRegistry` selects an adapter by ``provider/model``
logical name and supports an automatic mock fallback when no credentials are
configured (so the SDK is runnable out of the box).
"""

from __future__ import annotations

import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

from agentforge.exceptions import ProviderError
from agentforge.gateway import LLMRequest, LLMResponse
from agentforge.logging import get_logger
from agentforge.models import FinishReason, Message, ToolCall, Usage

logger = get_logger(__name__)


class BaseProvider(ABC):
    """Base class for provider adapters."""

    name: str = "base"

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    def _base_response(self, *, model: str, message: Message,
                       usage: Usage | None = None,
                       tool_calls: list[ToolCall] | None = None,
                       finish: FinishReason = FinishReason.STOP,
                       latency_ms: int = 0) -> LLMResponse:
        return LLMResponse(
            message=message,
            tool_calls=tool_calls or [],
            model=model,
            provider=self.name,
            usage=usage or Usage(),
            finish_reason=finish,
            latency_ms=latency_ms,
        )


class MockProvider(BaseProvider):
    """Deterministic, offline provider used for development and tests."""

    name = "mock"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        start = time.monotonic()
        last_user = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )
        # If the model requested tools, emit a single benign tool call occasionally.
        tool_calls: list[ToolCall] | None = None
        if request.tools:
            tool = request.tools[0]
            tname = tool.name if hasattr(tool, "name") else tool.get("function", {}).get("name")
            tool_calls = [
                ToolCall(
                    id=f"call_{uuid.uuid4().hex[:8]}",
                    function=__import__("agentforge.models", fromlist=["FunctionCall"]).FunctionCall(
                        name=tname, arguments=json.dumps({"query": last_user[:50]})
                    ),
                )
            ]
            content = ""
            finish = FinishReason.TOOL_CALLS
        else:
            content = f"[mock:{self.name}] {last_user}"
            finish = FinishReason.STOP
        usage = Usage(
            prompt_tokens=max(1, len(last_user) // 4),
            completion_tokens=max(1, len(content) // 4),
            cost_usd=0.0,
        )
        latency = int((time.monotonic() - start) * 1000)
        return self._base_response(
            model=request.model,
            message=Message(role="assistant", content=content, tool_calls=tool_calls),
            usage=usage,
            tool_calls=tool_calls,
            finish=finish,
            latency_ms=latency,
        )


class OpenAIProvider(BaseProvider):
    """Adapter for OpenAI-compatible chat completions."""

    name = "openai"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not set", provider=self.name)
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("httpx is required for OpenAI provider", provider=self.name, cause=exc)
        start = time.monotonic()
        payload: dict[str, Any] = {
            "model": request.model.split("/", 1)[-1],
            "messages": [m.to_dict() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "stream": False,
        }
        if request.tools:
            payload["tools"] = [t.to_openai() if hasattr(t, "to_openai") else t for t in request.tools]
            payload["tool_choice"] = request.tool_choice
        if request.response_format:
            payload["response_format"] = request.response_format
        try:
            async with httpx.AsyncClient(timeout=request.model and 120 or 120) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc), provider=self.name, cause=exc)
        latency = int((time.monotonic() - start) * 1000)
        return self._parse_openai(data, latency)

    def _parse_openai(self, data: dict[str, Any], latency: int) -> LLMResponse:
        choice = data["choices"][0]
        msg = choice["message"]
        content = msg.get("content", "") or ""
        tool_calls = None
        if msg.get("tool_calls"):
            from agentforge.models import FunctionCall, ToolCall

            tool_calls = [
                ToolCall(
                    id=tc["id"],
                    function=FunctionCall(name=tc["function"]["name"], arguments=tc["function"]["arguments"]),
                )
                for tc in msg["tool_calls"]
            ]
        finish = FinishReason(choice.get("finish_reason", "stop"))
        usage = Usage(
            prompt_tokens=data["usage"]["prompt_tokens"],
            completion_tokens=data["usage"]["completion_tokens"],
            cost_usd=_openai_cost(request_model=data.get("model", ""), usage=data["usage"]),
        )
        return self._base_response(
            model=data.get("model", ""),
            message=Message(role="assistant", content=content, tool_calls=tool_calls),
            usage=usage,
            tool_calls=tool_calls,
            finish=finish,
            latency_ms=latency,
        )


class AnthropicProvider(BaseProvider):
    """Adapter for Anthropic Messages API."""

    name = "anthropic"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set", provider=self.name)
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise ProviderError("httpx is required", provider=self.name, cause=exc)
        start = time.monotonic()
        system = [m.content for m in request.messages if m.role == "system"]
        messages = [
            m.to_dict() for m in request.messages if m.role in ("user", "assistant")
        ]
        payload: dict[str, Any] = {
            "model": request.model.split("/", 1)[-1],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
        }
        if system:
            payload["system"] = "\n".join(system)
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc), provider=self.name, cause=exc)
        latency = int((time.monotonic() - start) * 1000)
        text = "".join(block.get("text", "") for block in data.get("content", []))
        usage = Usage(
            prompt_tokens=data["usage"]["input_tokens"],
            completion_tokens=data["usage"]["output_tokens"],
        )
        return self._base_response(
            model=request.model,
            message=Message(role="assistant", content=text),
            usage=usage,
            latency_ms=latency,
        )


def _openai_cost(*, request_model: str, usage: dict[str, Any]) -> float:
    """Approximate cost estimate for OpenAI models (USD)."""
    pricing = {
        "gpt-4o": (0.005, 0.015),
        "gpt-4o-mini": (0.00015, 0.0006),
        "gpt-4-turbo": (0.01, 0.03),
        "gpt-3.5-turbo": (0.0005, 0.0015),
    }
    key = next((k for k in pricing if k in request_model), "gpt-4o-mini")
    inp, out = pricing[key]
    return round(inp * usage["prompt_tokens"] / 1000 + out * usage["completion_tokens"] / 1000, 6)


class ProviderRegistry:
    """Holds provider adapters and routes by logical name."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}
        self._mock = MockProvider()
        self.register(self._mock)
        self.register(OpenAIProvider())
        self.register(AnthropicProvider())

    def register(self, provider: BaseProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, logical: str) -> BaseProvider:
        name = logical.split("/", 1)[0].lower()
        provider = self._providers.get(name)
        if provider is None:
            logger.warning(
                "unknown provider '%s', falling back to mock", logical,
                extra={"attributes": {"provider": name}},
            )
            return self._mock
        # If a real provider has no credentials, transparently fall back to mock.
        if name in ("openai", "anthropic") and isinstance(provider, (OpenAIProvider, AnthropicProvider)):
            key = provider.api_key
            if not key:
                logger.info("no credentials for %s; using mock provider", name)
                return self._mock
        return provider


# Process-wide registry.
provider_registry = ProviderRegistry()
