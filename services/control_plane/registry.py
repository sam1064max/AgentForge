# SPDX-License-Identifier: Apache-2.0
"""AgentForge Control Plane - agent & deployment registry.

The control plane is the operational brain of the platform: it registers agent
definitions, manages their lifecycle (draft -> deployed -> paused -> archived),
and enforces tenant isolation. This local implementation uses an in-memory
store; production swaps in PostgreSQL (see docs/adr/0001) behind the same API.

Run locally:
    pip install fastapi uvicorn
    uvicorn services.control_plane.app:app --reload --port 8080
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class DeploymentStatus(str, Enum):
    DRAFT = "draft"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    PAUSED = "paused"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class AgentRecord:
    agent_id: str
    tenant_id: str
    name: str
    version: str
    description: str
    model: str
    entrypoint: str
    tools: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class DeploymentRecord:
    deployment_id: str
    agent_id: str
    tenant_id: str
    status: DeploymentStatus = DeploymentStatus.DRAFT
    replicas: int = 1
    region: str = "local"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: str | None = None


class ControlPlaneStore:
    """In-memory registry. Swap for PostgreSQL in production."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentRecord] = {}
        self._deployments: dict[str, DeploymentRecord] = {}

    # --- Agents -----------------------------------------------------------
    def create_agent(self, *, tenant_id: str, name: str, version: str, description: str,
                     model: str, entrypoint: str, tools: list[str] | None = None,
                     guardrails: list[str] | None = None, memory: dict[str, Any] | None = None,
                     tags: list[str] | None = None) -> AgentRecord:
        agent_id = f"agent-{uuid.uuid4().hex[:12]}"
        now = time.time()
        rec = AgentRecord(
            agent_id=agent_id, tenant_id=tenant_id, name=name, version=version,
            description=description, model=model, entrypoint=entrypoint,
            tools=tools or [], guardrails=guardrails or [], memory=memory or {},
            tags=tags or [], created_at=now, updated_at=now,
        )
        self._agents[agent_id] = rec
        return rec

    def get_agent(self, agent_id: str, *, tenant_id: str) -> AgentRecord | None:
        rec = self._agents.get(agent_id)
        if rec is None or rec.tenant_id != tenant_id:
            return None
        return rec

    def list_agents(self, *, tenant_id: str) -> list[AgentRecord]:
        return [a for a in self._agents.values() if a.tenant_id == tenant_id]

    def update_agent(self, agent_id: str, *, tenant_id: str, **fields: Any) -> AgentRecord | None:
        rec = self.get_agent(agent_id, tenant_id=tenant_id)
        if rec is None:
            return None
        for k, v in fields.items():
            if hasattr(rec, k):
                setattr(rec, k, v)
        rec.updated_at = time.time()
        return rec

    def delete_agent(self, agent_id: str, *, tenant_id: str) -> bool:
        rec = self.get_agent(agent_id, tenant_id=tenant_id)
        if rec is None:
            return False
        del self._agents[agent_id]
        return True

    # --- Deployments ------------------------------------------------------
    def deploy(self, *, tenant_id: str, agent_id: str, replicas: int = 1,
               region: str = "local") -> DeploymentRecord | None:
        rec = self.get_agent(agent_id, tenant_id=tenant_id)
        if rec is None:
            return None
        dep_id = f"dep-{uuid.uuid4().hex[:12]}"
        now = time.time()
        dep = DeploymentRecord(
            deployment_id=dep_id, agent_id=agent_id, tenant_id=tenant_id,
            status=DeploymentStatus.DEPLOYING, replicas=replicas, region=region,
            created_at=now, updated_at=now,
        )
        self._deployments[dep_id] = dep
        return dep

    def set_deployment_status(self, deployment_id: str, status: DeploymentStatus,
                              *, error: str | None = None) -> DeploymentRecord | None:
        dep = self._deployments.get(deployment_id)
        if dep is None:
            return None
        dep.status = status
        dep.error = error
        dep.updated_at = time.time()
        return dep

    def list_deployments(self, *, tenant_id: str) -> list[DeploymentRecord]:
        return [d for d in self._deployments.values() if d.tenant_id == tenant_id]


def _to_dict(rec: Any) -> dict[str, Any]:
    return asdict(rec)
