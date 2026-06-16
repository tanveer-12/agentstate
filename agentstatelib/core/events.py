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
    schema_version: int = 1


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


class ContextSliced(BaseStateEvent):
    """
    Emitted when a context slice is prepared for an agent.
    Records which state paths were included and how large the context was.
    Use this to understand what information each agent had access to and to debug cases
    where an agent made a wrong decision because it lacked necessary context.
    """

    type: Literal["context_sliced"] = "context_sliced"
    agent_id: str
    context_paths: list[str]
    context_size_bytes: int
    snapshot_workflow_id: str


class PromptAssembled(BaseStateEvent):
    """
    Emitted when a full prompt is assembled for a model call.
    Stores the complete prompt text so the replay debugger and web dashboard can
    show exactly what the model received.
    is_correction_attempt is True when the previous attempt failed validation and
    the error is appended to the prompt.
    """

    type: Literal["prompt_assembled"] = "prompt_assembled"
    agent_id: str
    prompt_text: str
    system_prompt_length: int
    context_length: int
    is_correction_attempt: bool
    attempt_number: int


class ModelCalled(BaseStateEvent):
    """
    Emitted immediately before a model API call is made.
    The call_id field links this event to the corresponding ModelReturned event so
    you can compute exact model call latency by taking the timestamp difference.
    """

    type: Literal["model_called"] = "model_called"
    agent_id: str
    model: str
    provider: str
    attempt_number: int
    call_id: str


class ModelReturned(BaseStateEvent):
    """
    Emitted immediately after a model call returns, before JSON parsing or validation.
    raw_response is the exact string the model produced. If the model returned
    malformed JSON, you will see the bad output here alongside the
    ValidationFailed event that follows.
    """

    type: Literal["model_returned"] = "model_returned"
    agent_id: str
    call_id: str
    raw_response: str
    latency_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None


class ValidationFailed(BaseStateEvent):
    """
    Emitted when a model response fails to parse as valid JSON or fails StatePatch
    schema validation. raw_output stores exactly what the model returned so you can
    diagnose patterns in model failures. will_retry indicates whether
    another attempt will follow.
    """

    type: Literal["validation_failed"] = "validation_failed"
    agent_id: str
    attempt_number: int
    error_type: Literal["json_decode_error", "schema_validation_error"]
    error_message: str
    raw_output: str
    will_retry: bool


class RetryAttempted(BaseStateEvent):
    """
    Emitted at the start of each retry attempt. previous_error contains
    the validation error from the last failure, which is appended
    to the correction prompt.
    """

    type: Literal["retry_attempted"] = "retry_attempted"
    agent_id: str
    attempt_number: int
    previous_error: str


class ToolCalled(BaseStateEvent):
    """
    Emitted when an agent invokes an external tool. Agents emit this
    manually: await workflow_store.append(ToolCalled(...)). A @trace_tool decorator
    helper is provided in agentstatelib.contrib.tracing.
    """

    type: Literal["tool_called"] = "tool_called"
    agent_id: str
    tool_name: str
    tool_input: dict[str, object]
    tool_call_id: str


class ToolReturned(BaseStateEvent):
    """
    Emitted when an external tool call completes. result_summary should be short
    enough to display inline in the dashboard timeline.
    """

    type: Literal["tool_returned"] = "tool_returned"
    agent_id: str
    tool_call_id: str
    success: bool
    result_summary: str
    latency_seconds: float
    error: str | None = None


class HumanApprovalRequested(BaseStateEvent):
    """
    Emitted when a workflow pauses for human review. The dashboard displays this as
    a pending action item. A human submits their decision via
    POST /v1/workflows/{id}/approvals/{approval_id}.
    """

    type: Literal["human_approval_requested"] = "human_approval_requested"
    agent_id: str
    approval_id: str
    description: str
    pending_patch: dict[str, object] | None = None
    timeout_seconds: int | None = None


class HumanApprovalResolved(BaseStateEvent):
    """
    Emitted when a human approves or rejects.
    """

    type: Literal["human_approval_resolved"] = "human_approval_resolved"
    agent_id: str
    approval_id: str
    decision: Literal["approved", "rejected", "modified"]
    reason: str | None = None
    modified_patch: dict[str, object] | None = None


StateEvent = Annotated[
    WorkflowStarted
    | WorkflowCompleted
    | PatchApplied
    | ConflictDetected
    | CheckpointSaved
    | AgentErrored
    | ContextSliced
    | PromptAssembled
    | ModelCalled
    | ModelReturned
    | ValidationFailed
    | RetryAttempted
    | ToolCalled
    | ToolReturned
    | HumanApprovalRequested
    | HumanApprovalResolved,
    Field(discriminator="type"),
]


# at module level, writing a typeadapter for statevent
# this is how you deserialize a JSON string into the correct event subtype
event_adapter: TypeAdapter[StateEvent] = TypeAdapter(StateEvent)
