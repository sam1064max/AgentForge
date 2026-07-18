"""Core data models for the AgentForge SDK.

These are the lingua franca of the platform: messages, tool calls, tool
definitions, and shared value types. They are intentionally provider-neutral
and serialize cleanly to/from JSON for the API and event bus.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Role = Literal["system", "user", "assistant", "tool"]


class Message(BaseModel):
    """A single chat message in an LLM conversation."""

    role: Role
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list["ToolCall"] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            data["name"] = self.name
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            data["tool_calls"] = [tc.to_openai() for tc in self.tool_calls]
        return data


class FunctionCall(BaseModel):
    """A function/tool invocation requested by the model."""

    name: str
    arguments: str  # JSON-encoded argument string (OpenAI-compatible)


class ToolCall(BaseModel):
    """A tool invocation emitted by the model."""

    id: str
    type: Literal["function"] = "function"
    function: FunctionCall

    def to_openai(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "function": self.function.model_dump(),
        }

    @classmethod
    def from_openai(cls, data: dict[str, Any]) -> "ToolCall":
        return cls(
            id=data["id"],
            type=data.get("type", "function"),
            function=FunctionCall(**data["function"]),
        )


class ToolDefinition(BaseModel):
    """Schema describing a tool offered to the model for function calling."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})
    strict: bool = False

    def to_openai(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class FunctionResult(BaseModel):
    """The result of executing a tool, fed back to the model."""

    tool_call_id: str
    name: str
    content: str
    is_error: bool = False

    def to_message(self) -> Message:
        return Message(role="tool", content=self.content, tool_call_id=self.tool_call_id, name=self.name)


class Usage(BaseModel):
    """Token and cost usage for an LLM interaction."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    @field_validator("total_tokens", mode="before")
    @classmethod
    def _default_total(cls, v: Any, info: Any) -> Any:
        if v:
            return v
        values = info.data
        return (values.get("prompt_tokens", 0) or 0) + (values.get("completion_tokens", 0) or 0)


class FinishReason(str, Enum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


Message.model_rebuild()
