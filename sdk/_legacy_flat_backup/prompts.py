"""In-process prompt registry.

Stores named prompt templates (Jinja2-compatible via stdlib `string.Template`
so there are no hard dependencies) and renders them with variables. Production
deployments use the Prompt Registry service; this local version keeps agents
runnable offline.
"""

from __future__ import annotations

import threading
from typing import Any

from agentforge.logging import get_logger

logger = get_logger(__name__)


class PromptRegistry:
    """Holds named prompt templates and renders them with variables."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}
        self._lock = threading.RLock()

    def register(self, name: str, template: str, *, overwrite: bool = False) -> None:
        with self._lock:
            if name in self._templates and not overwrite:
                raise ValueError(f"Prompt '{name}' already registered")
            self._templates[name] = template

    def get(self, name: str) -> str:
        with self._lock:
            if name not in self._templates:
                raise KeyError(f"Prompt '{name}' not found")
            return self._templates[name]

    def render(self, name: str, **variables: Any) -> str:
        template = self.get(name)
        try:
            from string import Template

            return Template(template).safe_substitute(**{k: str(v) for k, v in variables.items()})
        except Exception as exc:  # noqa: BLE001
            logger.warning("prompt render failed", extra={"attributes": {"prompt": name, "error": str(exc)}})
            return template

    def list(self) -> list[str]:
        with self._lock:
            return list(self._templates.keys())
