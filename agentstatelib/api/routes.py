from __future__ import annotations

import asyncio
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from agentstatelib.api.auth import is_valid_key, verify_api_key
from agentstatelib.api.dashboard import DASHBOARD_HTML
from agentstatelib.api.streaming import stream_workflow_events
from agentstatelib.core.events import PatchApplied, WorkflowStarted
from agentstatelib.core.patch import StatePatch
from agentstatelib.core.state import SharedState
from agentstatelib.memory.replay import get_agent_turns
from agentstatelib.memory.store import StateStore
from agentstatelib.router.graph import PendingApproval

# All API errors use:
#
# {
#     "error_code": "...",
#     "message": "..."
# }
#
# Never return plain string error messages.


def get_store(request: Request) -> StateStore:
    """FastAPI dependency that returns the shared StateStore from app.state"""
    return cast(StateStore, request.app.state.store)


class CreateWorkflowRequest(BaseModel):
    goal: str
    workflow_type: str = "general"


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approved", "rejected", "modified"]
    reason: str | None = None
    modified_patch: StatePatch | None = None


class PendingApprovalResponse(BaseModel):
    approval_id: str
    workflow_id: str
    agent_id: str
    description: str
    patch: dict[str, object]


router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """
    Health check.
    Returns immediately with no side effects.
    No authentication required. Used by load balancers and monitoring systems.
    """
    return {"status": "ok", "version": "0.5.0"}


@router.get("/workflows", tags=["workflows"])
async def list_workflows(
    _: str = Depends(verify_api_key),
    store: StateStore = Depends(get_store),
) -> dict[str, object]:
    """List all workflow IDs in the store,
    most recent first."""
    workflow_ids = await store.list_workflows()
    return {"workflow_ids": workflow_ids, "count": len(workflow_ids)}


@router.post("/workflows", status_code=201, tags=["workflows"])
async def create_workflow(
    body: CreateWorkflowRequest,
    _: str = Depends(verify_api_key),
    store: StateStore = Depends(get_store),
) -> SharedState:
    """
    Create a new Workflow.
    Returns the initial SharedState with a generated workflow_id.
    """
    state = SharedState(
        goal=body.goal,
        workflow_type=body.workflow_type,
    )
    event = WorkflowStarted(
        workflow_id=state.workflow_id,
        agent_id="system",
        workflow_type=body.workflow_type,
        goal=body.goal,
    )
    await store.append(event)
    return state


@router.get("/workflows/{workflow_id}", tags=["workflows"])
async def get_workflow(
    workflow_id: str,
    _: str = Depends(verify_api_key),
    store: StateStore = Depends(get_store),
) -> SharedState:
    """
    Get the current reconstructed state of a workflow
    by replaying its event log.
    """
    events = await store.get_workflow(workflow_id)
    if not events:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "workflow_not_found",
                "message": (f"No events found for workflow {workflow_id!r}"),
            },
        )
    from agentstatelib.memory.replay import replay

    return replay(events)


@router.post("/workflows/{workflow_id}/patches", tags=["workflows"])
async def submit_patch(
    workflow_id: str,
    patch: StatePatch,
    _: str = Depends(verify_api_key),
    store: StateStore = Depends(get_store),
) -> SharedState:
    """
    Submit a patch to a workflow outside of a graph run.

    Useful for human-in-the-loop scenarios where a
    person reviews and approves a state change before
    the workflow continues.
    """
    events = await store.get_workflow(workflow_id)
    if not events:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "workflow_not_found",
                "message": (f"No events found for workflow {workflow_id!r}"),
            },
        )
    patch_event = PatchApplied(
        workflow_id=workflow_id,
        agent_id=patch.agent_id,
        patch_id=patch.patch_id,
        target=patch.target,
        old_value=None,
        new_value=patch.value,
        reason=patch.reason,
        timestamp=patch.timestamp,
    )
    await store.append(patch_event)

    from agentstatelib.memory.replay import replay

    events = await store.get_workflow(workflow_id)
    return replay(events)


@router.get(
    "/workflows/{workflow_id}/events",
    tags=["workflows"],
)
async def workflow_events(
    workflow_id: str,
    request: Request,
    key: str | None = Query(None),
    store: StateStore = Depends(get_store),
) -> StreamingResponse:
    """
    Stream workflow events as Server-Sent Events.

    Accepts authentication via x-api-key header or
    key query parameter.

    The query parameter is required for browser
    EventSource connections.
    """
    header_key = request.headers.get("x-api-key")

    authenticated = False

    if header_key and is_valid_key(header_key):
        authenticated = True

    elif key and is_valid_key(key):
        authenticated = True

    if not authenticated:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "invalid_api_key",
                "message": (
                    "Invalid or missing API key. "
                    "Set valid keys via the AGENTSTATE_API_KEYS "
                    "environment variable as a comma-separated list."
                ),
            },
        )

    return StreamingResponse(
        stream_workflow_events(
            store,
            workflow_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/workflows/{workflow_id}/events-list",
    tags=["workflows"],
)
async def workflow_event_list(
    workflow_id: str,
    _: str = Depends(verify_api_key),
    store: StateStore = Depends(get_store),
) -> dict[str, object]:
    """
    Get all events for a workflow as a JSON array.

    Used by the web dashboard to load workflow
    history without a streaming connection.
    """
    events = await store.get_workflow(workflow_id)

    return {
        "events": [event.model_dump() for event in events],
        "count": len(events),
    }


@router.get("/workflows/{workflow_id}/turns", tags=["workflows"])
async def workflow_turns(
    workflow_id: str,
    _: str = Depends(verify_api_key),
    store: StateStore = Depends(get_store),
) -> dict[str, object]:
    events = await store.get_workflow(workflow_id)
    if not events:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "workflow_not_found",
                "message": f"No events found for workflow {workflow_id!r}",
            },
        )

    turns = get_agent_turns(events)
    payload: list[dict[str, object]] = []

    for turn in turns:
        context_paths = turn.context_sliced.context_paths if turn.context_sliced else []
        first_prompt_preview = turn.prompts[0].prompt_text[:150] if turn.prompts else ""
        model = turn.model_calls[0][0].model if turn.model_calls else ""
        patch_target = turn.patch_applied.target if turn.patch_applied else ""
        patch_reason = turn.patch_applied.reason if turn.patch_applied else ""

        payload.append(
            {
                "agent_id": turn.agent_id,
                "attempt_count": turn.attempt_count,
                "succeeded": turn.succeeded,
                "total_latency_seconds": turn.total_latency_seconds,
                "total_tokens": turn.total_tokens,
                "context_paths": context_paths,
                "first_prompt_preview": first_prompt_preview,
                "model": model,
                "validation_failure_count": len(turn.validation_failures),
                "patch_target": patch_target,
                "patch_reason": patch_reason,
            }
        )

    return {"turns": payload, "count": len(payload)}


@router.get("/workflows/{workflow_id}/approvals", tags=["workflows"])
async def list_approvals(
    workflow_id: str,
    request: Request,
    _: str = Depends(verify_api_key),
) -> dict[str, object]:
    """
    Return all pending approvals for a workflow.

    Reads directly from the AgentGraph instance so the list is always
    in sync with what the graph is actually waiting on.
    """
    graph = request.app.state.graph
    pending_approvals: dict[str, PendingApproval] = getattr(graph, "pending_approvals", {})
    items = [
        {
            "approval_id": approval_id,
            "workflow_id": item.workflow_id,
            "agent_id": item.agent_id,
            "description": item.description,
            "patch": item.patch.model_dump(),
        }
        for approval_id, item in pending_approvals.items()
        if item.workflow_id == workflow_id
    ]
    return {"approvals": items, "count": len(items)}


@router.post("/workflows/{workflow_id}/approvals/{approval_id}", tags=["workflows"])
async def submit_approval(
    workflow_id: str,
    approval_id: str,
    body: ApprovalDecisionRequest,
    request: Request,
    _: str = Depends(verify_api_key),
) -> dict[str, object]:
    """
    Submit an approval decision for a pending patch.

    The graph applies the patch (or modified patch) to state and emits
    HumanApprovalResolved. Returns the decision summary.
    """
    graph = request.app.state.graph
    pending_approvals: dict[str, PendingApproval] = getattr(graph, "pending_approvals", {})
    pending = pending_approvals.get(approval_id)

    if pending is None or pending.workflow_id != workflow_id:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "approval_not_found",
                "message": f"No pending approval {approval_id!r} for workflow {workflow_id!r}",
            },
        )

    await graph.resume_from_approval(
        approval_id=approval_id,
        decision=body.decision,
        modified_patch=body.modified_patch,
    )

    return {
        "approval_id": approval_id,
        "workflow_id": workflow_id,
        "decision": body.decision,
        "reason": body.reason,
    }
