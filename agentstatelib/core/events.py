import time
import uuid
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter

from agentstatelib.core.state import WorkflowStatus


# This is the parent all events share
class BaseStateEvent(BaseModel):
    """
    Base class for all events in the agentstatelib event log.

    Every state change, conflict, checkpoint, and error produces a typed
    event appended to the store. Events are immutable once written.
    """

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    agent_id: str
    timestamp: float = Field(default_factory=time.time)


class WorkflowStarted(BaseStateEvent):
    """
    Emitted at the start of AgentGraph.run().

    Marks the beginning of the event sequence and carries the workflow
    metadata needed to reconstruct SharedState from scratch during replay.
    """

    type: Literal["workflow_started"] = "workflow_started"
    workflow_type: str
    goal: str


class WorkflowCompleted(BaseStateEvent):
    """
    Emitted when AgentGraph.run() finishes normally.

    final_status is the workflow status at the time of completion.
    """

    type: Literal["workflow_completed"] = "workflow_completed"
    final_status: WorkflowStatus


class PatchApplied(BaseStateEvent):
    """
    Emitted after a winning patch is applied to state.

    old_value and new_value store only the value at patch.target —
    not full state dumps. This keeps individual events compact
    regardless of overall state size.
    """

    type: Literal["patch_applied"] = "patch_applied"
    patch_id: str
    target: str
    old_value: Any
    new_value: Any
    reason: str


class ConflictDetected(BaseStateEvent):
    """
    Emitted when resolve_batch() detects two patches targeting the same
    state path in the same parallel round.

    Both patches stored as plain dicts rather than StatePatch objects
    to guarantee JSON serializability regardless of what value fields
    contain.
    """

    type: Literal["conflict_detected"] = "conflict_detected"
    conflict_id: str
    path: str
    winner_agent_id: str
    loser_agent_id: str
    resolution_strategy: str
    existing_patch: dict[str, object] | None = None
    incoming_patch: dict[str, object] | None = None


class CheckpointSaved(BaseStateEvent):
    """Emitted when save_checkpoint() completes successfully."""

    type: Literal["checkpoint_saved"] = "checkpoint_saved"
    checkpoint_id: str
    event_count: int


class AgentErrored(BaseStateEvent):
    """
    Emitted when an agent raises an unhandled exception.

    retry_count records how many retries were attempted.
    """

    type: Literal["agent_errored"] = "agent_errored"
    error_type: str
    error_message: str
    retry_count: int


StateEvent = Annotated[
    WorkflowStarted
    | WorkflowCompleted
    | PatchApplied
    | ConflictDetected
    | CheckpointSaved
    | AgentErrored,
    Field(discriminator="type"),
]

# at module level, writing a typeadapter for statevent
# this is how you deserialize a JSON string into the correct event subtype
event_adapter: TypeAdapter[StateEvent] = TypeAdapter(StateEvent)
