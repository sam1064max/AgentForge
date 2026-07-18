# SPDX-License-Identifier: Apache-2.0
"""Prompt registry: versioned, typed, renderable prompt templates."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PromptStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


@dataclass(slots=True)
class PromptVariable:
    name: str
    type: str = "string"
    required: bool = True
    default: Any = None
    description: str = ""


@dataclass(slots=True)
class PromptTemplate:
    """A versioned prompt template."""

    name: str
    template: str
    tenant_id: str = "default"
    version: str = "1.0.0"
    variables: list[PromptVariable] = field(default_factory=list)
    status: PromptStatus = PromptStatus.ACTIVE
    tags: list[str] = field(default_factory=list)
    model_compatibility: list[str] = field(default_factory=list)
    changelog: str | None = None

    def render(self, **values: Any) -> str:
        """Render the template, substituting ``{{var}}`` placeholders.

        Supports ``{{#each items}}...{{this}}...{{/each}}`` iteration and
        ``{{#if cond}}...{{/if}}`` conditionals, matching the architecture's
        Handlebars-flavoured template contract.
        """
        return _render(self.template, values)


_VAR = re.compile(r"{{\s*([\w.]+)\s*}}")
_EACH = re.compile(r"{{#each\s+(\w+)\s*}}(.*?){{/each}}", re.DOTALL)
_IF = re.compile(r"{{#if\s+(\w+)\s*}}(.*?)(?:{{else}}(.*?))?{{/if}}", re.DOTALL)


def _lookup(values: dict[str, Any], path: str) -> Any:
    cur: Any = values
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _render(template: str, values: dict[str, Any]) -> str:
    def replace_var(match: re.Match[str]) -> str:
        value = _lookup(values, match.group(1))
        return "" if value is None else str(value)

    # Iteration blocks
    def replace_each(match: re.Match[str]) -> str:
        key = match.group(1)
        body = match.group(2)
        items = values.get(key, [])
        if not isinstance(items, (list, tuple)):
            items = [items]
        out = []
        for item in items:
            local = dict(values)
            if isinstance(item, dict):
                local.update(item)
                out.append(_render(body, local).replace("{{this}}", ""))
            else:
                out.append(_render(body, {**values, "this": item}))
        return "".join(out)

    template = _EACH.sub(replace_each, template)
    template = _IF.sub(lambda m: m.group(2) if _lookup(values, m.group(1)) else (m.group(3) or ""), template)
    template = _VAR.sub(replace_var, template)
    return template


class PromptRegistry:
    """In-process registry of prompt templates keyed by ``tenant:name:version``."""

    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}

    def register(self, template: PromptTemplate) -> None:
        key = f"{template.tenant_id}:{template.name}:{template.version}"
        self._templates[key] = template

    def get(self, name: str, *, tenant_id: str = "default", version: str | None = None) -> PromptTemplate:
        if version:
            tpl = self._templates.get(f"{tenant_id}:{name}:{version}")
            if tpl is None:
                raise KeyError(f"Prompt {name}@{version} not found for tenant {tenant_id}")
            return tpl
        # Return the latest ACTIVE version.
        candidates = [
            t for t in self._templates.values()
            if t.tenant_id == tenant_id and t.name == name
        ]
        if not candidates:
            raise KeyError(f"Prompt {name} not found for tenant {tenant_id}")
        active = [c for c in candidates if c.status == PromptStatus.ACTIVE]
        pool = active or candidates
        return sorted(pool, key=lambda t: t.version, reverse=True)[0]
