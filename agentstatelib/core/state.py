import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

WorkflowStatus = Literal["running", "complete", "failed", "paused"]


class Task(BaseModel):
    """
    A unit of work withing a workflow.
    May optionally belong to a Goal via goal_id. When goal_id is None
    the task is ungrouped and not checked by goal-based invariants.
    The result field stores agent output after the task completes.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str | None = None
    description: str
    status: Literal["pending", "running", "done", "failed"] = "pending"
    result: Any | None = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class Goal(BaseModel):
    """
    A high-level objective that groups related Tasks.

    Goals are optional - workflows that use only facts and artifacts
    do not need them.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    status: Literal["pending", "active", "complete", "failed"] = "pending"
    created_at: float = Field(default_factory=time.time)


class Artifact(BaseModel):
    """
    An output produced by an agent and stored in shared state.

    artifact_type is a free-form string — use whatever names make sense
    for your workflow domain, such as 'draft', 'source', or 'summary'.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    produced_by: str
    artifact_type: str
    content: Any
    created_at: float = Field(default_factory=time.time)


class Decision(BaseModel):
    """
    A recorded workflow decision with rationale.

    Append to SharedState.decisions when an agent makes a significant
    choice that downstream agents or human reviewers should be able
    to audit.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    made_by: str
    description: str
    rationale: str
    timestamp: float = Field(default_factory=time.time)


class SharedState(BaseModel):
    """
    The single source of truth for a workflow.

    Never mutated directly — all changes go through StatePatch and
    apply_patch which return a new SharedState object.

    All agents in a parallel round read the same SharedState snapshot,
    guaranteeing consistent reads within a round with no intra-round races.

    The event log stores the sequence of patches applied to state, so any
    past state can be reconstructed by replaying the log.
    """

    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_type: str = "general"
    goal: str
    goals: dict[str, Goal] = Field(default_factory=dict)
    tasks: dict[str, Task] = Field(default_factory=dict)
    artifacts: dict[str, Artifact] = Field(default_factory=dict)
    decisions: list[Decision] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)
    status: WorkflowStatus = "running"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
