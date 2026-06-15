"""
Integration tests for the human-in-the-loop approval flow.

Covers the full end-to-end path:
  graph emits HumanApprovalRequested
  → approval stored in graph.pending_approvals
  → HTTP GET /v1/workflows/{id}/approvals returns it
  → HTTP POST /v1/workflows/{id}/approvals/{approval_id} resolves it
  → graph.resume_from_approval applies the patch and emits HumanApprovalResolved
  → state is updated correctly
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agentstatelib.api.app import create_app
from agentstatelib.core.events import HumanApprovalRequested, HumanApprovalResolved
from agentstatelib.core.patch import StatePatch
from agentstatelib.core.state import SharedState
from agentstatelib.memory.store import InMemoryStore
from agentstatelib.router.graph import AgentGraph

AUTH_HEADERS = {"x-api-key": "dev-key-123"}


# ── graph-level tests (no HTTP) ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_graph_emits_approval_requested_and_pauses_patch() -> None:
    """Patch guarded by approval_required is NOT applied; event IS emitted."""
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    @graph.node("writer", context=["goal"])
    async def writer(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="writer",
            target="facts.important",
            value="new_value",
            reason="important change",
        )

    graph.edge(
        "writer",
        "writer",
        condition=lambda _s: False,  # terminal — no next round
        approval_required=lambda _state, _patch: True,  # always gate
    )

    state = SharedState(goal="test approval gate", workflow_type="test")
    await graph.run(state, start="writer")

    events = await store.get_workflow(state.workflow_id)
    approval_events = [e for e in events if isinstance(e, HumanApprovalRequested)]

    assert len(approval_events) == 1
    ev = approval_events[0]
    assert ev.description == "important change"
    assert ev.pending_patch is not None
    assert ev.pending_patch["target"] == "facts.important"


@pytest.mark.asyncio
async def test_resume_from_approval_approved_applies_patch() -> None:
    """Approving a pending patch updates state and returns the new SharedState."""
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    @graph.node("writer", context=["goal"])
    async def writer(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="writer",
            target="facts.key",
            value="approved_value",
            reason="needs approval",
        )

    graph.edge(
        "writer",
        "writer",
        condition=lambda _s: False,
        approval_required=lambda _state, _patch: True,
    )

    state = SharedState(goal="approval test", workflow_type="test")
    await graph.run(state, start="writer")

    assert len(graph.pending_approvals) == 1
    approval_id = next(iter(graph.pending_approvals))

    new_state = await graph.resume_from_approval(
        approval_id=approval_id,
        decision="approved",
        modified_patch=None,
    )

    assert new_state is not None
    assert new_state.facts["key"] == "approved_value"  # type: ignore[index]
    assert len(graph.pending_approvals) == 0

    events = await store.get_workflow(state.workflow_id)
    resolved_events = [e for e in events if isinstance(e, HumanApprovalResolved)]
    assert len(resolved_events) == 1
    assert resolved_events[0].decision == "approved"


@pytest.mark.asyncio
async def test_resume_from_approval_rejected_discards_patch() -> None:
    """Rejecting a pending approval returns None and does not touch state."""
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    @graph.node("writer", context=["goal"])
    async def writer(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="writer",
            target="facts.key",
            value="rejected_value",
            reason="needs approval",
        )

    graph.edge(
        "writer",
        "writer",
        condition=lambda _s: False,
        approval_required=lambda _state, _patch: True,
    )

    state = SharedState(goal="rejection test", workflow_type="test")
    await graph.run(state, start="writer")

    approval_id = next(iter(graph.pending_approvals))
    result = await graph.resume_from_approval(
        approval_id=approval_id,
        decision="rejected",
        modified_patch=None,
    )

    assert result is None
    assert len(graph.pending_approvals) == 0

    events = await store.get_workflow(state.workflow_id)
    resolved_events = [e for e in events if isinstance(e, HumanApprovalResolved)]
    assert len(resolved_events) == 1
    assert resolved_events[0].decision == "rejected"


@pytest.mark.asyncio
async def test_resume_from_approval_modified_applies_modified_patch() -> None:
    """Modified decision applies the reviewer's patch, not the original."""
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    @graph.node("writer", context=["goal"])
    async def writer(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="writer",
            target="facts.key",
            value="original_value",
            reason="needs approval",
        )

    graph.edge(
        "writer",
        "writer",
        condition=lambda _s: False,
        approval_required=lambda _state, _patch: True,
    )

    state = SharedState(goal="modify test", workflow_type="test")
    await graph.run(state, start="writer")

    approval_id = next(iter(graph.pending_approvals))
    modified = StatePatch(
        agent_id="human",
        target="facts.key",
        value="human_corrected_value",
        reason="human override",
    )
    new_state = await graph.resume_from_approval(
        approval_id=approval_id,
        decision="modified",
        modified_patch=modified,
    )

    assert new_state is not None
    assert new_state.facts["key"] == "human_corrected_value"  # type: ignore[index]


@pytest.mark.asyncio
async def test_resume_from_approval_unknown_id_raises() -> None:
    """resume_from_approval raises KeyError on an unknown approval_id."""
    graph = AgentGraph()
    with pytest.raises(KeyError):
        await graph.resume_from_approval(
            approval_id="nonexistent",
            decision="approved",
            modified_patch=None,
        )


# ── HTTP endpoint tests ────────────────────────────────────────────────────────


@pytest.fixture
def client_with_pending_approval(tmp_path):  # type: ignore[no-untyped-def]
    """
    Returns (TestClient, workflow_id) with one pre-populated pending approval.

    We inject into graph.pending_approvals directly to avoid running async code
    inside a sync fixture (Python 3.12 has no default event loop in the main thread).
    """
    from agentstatelib.router.graph import PendingApproval

    app = create_app(db_path=str(tmp_path / "test.db"))
    graph: AgentGraph = app.state.graph

    state = SharedState(goal="http test", workflow_type="test")
    patch = StatePatch(
        agent_id="writer",
        target="facts.http_key",
        value="http_value",
        reason="http approval test",
    )
    approval_id = "test-approval-http-001"
    graph.pending_approvals[approval_id] = PendingApproval(
        workflow_id=state.workflow_id,
        state=state,
        patch=patch,
        agent_id="writer",
        description="http approval test",
    )

    return TestClient(app), state.workflow_id


def test_list_approvals_returns_pending(client_with_pending_approval) -> None:  # type: ignore[no-untyped-def]
    client, workflow_id = client_with_pending_approval
    response = client.get(
        f"/v1/workflows/{workflow_id}/approvals",
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    approval = data["approvals"][0]
    assert approval["workflow_id"] == workflow_id
    assert approval["description"] == "http approval test"
    assert "approval_id" in approval


def test_submit_approval_approved(client_with_pending_approval) -> None:  # type: ignore[no-untyped-def]
    client, workflow_id = client_with_pending_approval

    list_resp = client.get(
        f"/v1/workflows/{workflow_id}/approvals",
        headers=AUTH_HEADERS,
    )
    approval_id = list_resp.json()["approvals"][0]["approval_id"]

    post_resp = client.post(
        f"/v1/workflows/{workflow_id}/approvals/{approval_id}",
        headers=AUTH_HEADERS,
        json={"decision": "approved"},
    )
    assert post_resp.status_code == 200
    data = post_resp.json()
    assert data["decision"] == "approved"
    assert data["approval_id"] == approval_id

    # Approval should be gone from the list
    list_resp2 = client.get(
        f"/v1/workflows/{workflow_id}/approvals",
        headers=AUTH_HEADERS,
    )
    assert list_resp2.json()["count"] == 0


def test_submit_approval_unknown_id_returns_404(client_with_pending_approval) -> None:  # type: ignore[no-untyped-def]
    client, workflow_id = client_with_pending_approval
    response = client.post(
        f"/v1/workflows/{workflow_id}/approvals/nonexistent-id",
        headers=AUTH_HEADERS,
        json={"decision": "approved"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "approval_not_found"


def test_list_approvals_requires_auth(client_with_pending_approval) -> None:  # type: ignore[no-untyped-def]
    client, workflow_id = client_with_pending_approval
    response = client.get(f"/v1/workflows/{workflow_id}/approvals")
    assert response.status_code == 401
