# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the AgentForge control-plane registry (tenant isolation)."""

from __future__ import annotations

from services.control_plane.registry import ControlPlaneStore, DeploymentStatus


def _seed(store: ControlPlaneStore) -> str:
    rec = store.create_agent(
        tenant_id="acme", name="support", version="1.0.0",
        description="Support agent", model="openai/gpt-4o",
        entrypoint="examples/order_agent.py", tools=["lookup_order"],
        guardrails=["pii-detection"],
    )
    return rec.agent_id


def test_create_and_get():
    s = ControlPlaneStore()
    aid = _seed(s)
    rec = s.get_agent(aid, tenant_id="acme")
    assert rec is not None
    assert rec.name == "support"


def test_tenant_isolation():
    s = ControlPlaneStore()
    aid = _seed(s)
    # A different tenant must not see the agent.
    assert s.get_agent(aid, tenant_id="evil-co") is None
    assert s.list_agents(tenant_id="evil-co") == []


def test_update_and_delete():
    s = ControlPlaneStore()
    aid = _seed(s)
    s.update_agent(aid, tenant_id="acme", description="Updated")
    assert s.get_agent(aid, tenant_id="acme").description == "Updated"
    assert s.delete_agent(aid, tenant_id="acme") is True
    assert s.get_agent(aid, tenant_id="acme") is None


def test_deploy_lifecycle():
    s = ControlPlaneStore()
    aid = _seed(s)
    dep = s.deploy(tenant_id="acme", agent_id=aid, replicas=2)
    assert dep is not None
    assert dep.status == DeploymentStatus.DEPLOYING
    s.set_deployment_status(dep.deployment_id, DeploymentStatus.DEPLOYED)
    assert s._deployments[dep.deployment_id].status == DeploymentStatus.DEPLOYED
    assert len(s.list_deployments(tenant_id="acme")) == 1


def test_deploy_unknown_agent():
    s = ControlPlaneStore()
    assert s.deploy(tenant_id="acme", agent_id="nope") is None
