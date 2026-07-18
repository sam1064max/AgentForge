"""Structured logging for AgentForge.

Provides a module-level :func:`get_logger` that emits JSON-structured records
compatible with the platform's observability pipeline. Falls back to stdlib
``logging`` when no structured sink is configured.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

# Context variables propagated across async boundaries.
tenant_id_var: ContextVar[str | None] = ContextVar("af_tenant_id", default=None)
agent_id_var: ContextVar[str | None] = ContextVar("af_agent_id", default=None)
execution_id_var: ContextVar[str | None] = ContextVar("af_execution_id", default=None)
trace_id_var: ContextVar[str | None] = ContextVar("af_trace_id", default=None)

_LOG_LEVEL = os.environ.get("AGENTFORGE_LOG_LEVEL", "INFO").upper()


class JsonFormatter(logging.Formatter):
    """Emits one JSON object per log line with AgentForge semantic fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "service": getattr(record, "service", "agentforge-sdk"),
            "message": record.getMessage(),
        }
        tenant = tenant_id_var.get()
        agent = agent_id_var.get()
        execution = execution_id_var.get()
        trace = trace_id_var.get()
        if tenant:
            payload["tenant_id"] = tenant
        if agent:
            payload["agent_id"] = agent
        if execution:
            payload["execution_id"] = execution
        if trace:
            payload["trace_id"] = trace
        attrs = getattr(record, "attributes", None)
        if isinstance(attrs, dict):
            payload["attributes"] = attrs
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(name: str, *, service: str = "agentforge-sdk") -> logging.Logger:
    """Return a configured logger. Idempotent for a given name."""
    logger = logging.getLogger(name)
    if getattr(logger, "_af_configured", False):
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(_LOG_LEVEL)
    logger.propagate = False
    setattr(logger, "_af_configured", True)
    # Attach service name to records.
    old_factory = logging.getLogRecordFactory()

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "service"):
            record.service = service  # type: ignore[attr-defined]
        return record

    logging.setLogRecordFactory(factory)
    return logger


def new_trace_id() -> str:
    """Generate a W3C-style trace id (32 hex chars)."""
    return uuid.uuid4().hex


def bind_context(
    *,
    tenant_id: str | None = None,
    agent_id: str | None = None,
    execution_id: str | None = None,
    trace_id: str | None = None,
) -> None:
    """Bind observability context for the current async task."""
    if tenant_id is not None:
        tenant_id_var.set(tenant_id)
    if agent_id is not None:
        agent_id_var.set(agent_id)
    if execution_id is not None:
        execution_id_var.set(execution_id)
    if trace_id is not None:
        trace_id_var.set(trace_id)
