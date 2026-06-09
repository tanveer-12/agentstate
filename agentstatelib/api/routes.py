from __future__ import annotations

import asyncio
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from agentstatelib.api.auth import is_valid_key, verify_api_key
from agentstatelib.api.streaming import stream_workflow_events
from agentstatelib.core.events import PatchApplied, WorkflowStarted
from agentstatelib.core.patch import StatePatch
from agentstatelib.core.state import SharedState
from agentstatelib.memory.store import StateStore

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


router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """
    Health check.
    Returns immediately with no side effects.
    No authentication required. Used by load balancers and monitoring systems.
    """
    return {"status": "ok", "version": "0.2.0"}


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
    by replacing its event log.
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
