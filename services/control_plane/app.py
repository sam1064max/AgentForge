# SPDX-License-Identifier: Apache-2.0
"""FastAPI application for the AgentForge control plane.

Exposes a tenant-scoped REST API for registering agents and managing their
deployments. All handlers resolve the tenant from the ``X-Tenant-Id`` header
(or fall back to a default) to enforce isolation at the API boundary.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Header

from services.control_plane.registry import (
    ControlPlaneStore,
    DeploymentStatus,
)

app = FastAPI(title="AgentForge Control Plane", version="0.1.0")
store = ControlPlaneStore()


def _tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    return x_tenant_id


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/agents")
async def create_agent(body: dict[str, Any], tenant_id: str = _tenant_id()):
    try:
        rec = store.create_agent(tenant_id=tenant_id, **body)
    except TypeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _dict(rec)


@app.get("/agents")
async def list_agents(tenant_id: str = _tenant_id()):
    return [_dict(a) for a in store.list_agents(tenant_id=tenant_id)]


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str, tenant_id: str = _tenant_id()):
    rec = store.get_agent(agent_id, tenant_id=tenant_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return _dict(rec)


@app.patch("/agents/{agent_id}")
async def update_agent(agent_id: str, body: dict[str, Any], tenant_id: str = _tenant_id()):
    rec = store.update_agent(agent_id, tenant_id=tenant_id, **body)
    if rec is None:
        raise HTTPException(status_code=404, detail="agent not found")
    return _dict(rec)


@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, tenant_id: str = _tenant_id()):
    if not store.delete_agent(agent_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="agent not found")
    return {"deleted": agent_id}


@app.post("/agents/{agent_id}/deploy")
async def deploy_agent(agent_id: str, body: dict[str, Any] | None = None,
                       tenant_id: str = _tenant_id()):
    body = body or {}
    dep = store.deploy(tenant_id=tenant_id, agent_id=agent_id,
                       replicas=int(body.get("replicas", 1)),
                       region=body.get("region", "local"))
    if dep is None:
        raise HTTPException(status_code=404, detail="agent not found")
    # Simulate the deploy controller promoting to deployed.
    store.set_deployment_status(dep.deployment_id, DeploymentStatus.DEPLOYED)
    return _dict(store._deployments[dep.deployment_id])


@app.get("/deployments")
async def list_deployments(tenant_id: str = _tenant_id()):
    return [_dict(d) for d in store.list_deployments(tenant_id=tenant_id)]


def _dict(rec: Any) -> dict[str, Any]:
    import dataclasses

    return dataclasses.asdict(rec)
