from __future__ import annotations

from agentstatelib.coordination import (
    BatchResolutionResult,
    ConflictResolver,
    InvariantChecker,
    InvariantViolation,
    LastWriteWins,
    PriorityBased,
    RejectIncoming,
)
from agentstatelib.core.events import (
    AgentErrored,
    BaseStateEvent,
    CheckpointSaved,
    ConflictDetected,
    PatchApplied,
    StateEvent,
    WorkflowCompleted,
    WorkflowStarted,
    event_adapter,
)
from agentstatelib.core.patch import (
    StatePatch,
    apply_patch,
    get_nested,
    set_nested,
)
from agentstatelib.core.state import (
    Artifact,
    Decision,
    Goal,
    SharedState,
    Task,
    WorkflowStatus,
)
from agentstatelib.memory.checkpoint import (
    Checkpoint,
    load_latest_checkpoint,
    save_checkpoint,
)
from agentstatelib.memory.replay import ReplayDebugger, replay
from agentstatelib.memory.store import (
    InMemoryStore,
    PostgreSQLStore,
    SQLiteStore,
    StateStore,
)
from agentstatelib.router.context import slice_state
from agentstatelib.router.graph import AgentGraph, EventQueue, WorkflowEvent
from agentstatelib.router.types import AgentFn, EdgeCondition

__version__ = "0.2.0"

__all__ = [
    "SharedState",
    "Task",
    "Goal",
    "Artifact",
    "Decision",
    "WorkflowStatus",
    "StatePatch",
    "apply_patch",
    "set_nested",
    "get_nested",
    "StateEvent",
    "BaseStateEvent",
    "WorkflowStarted",
    "WorkflowCompleted",
    "PatchApplied",
    "ConflictDetected",
    "CheckpointSaved",
    "AgentErrored",
    "event_adapter",
    "AgentGraph",
    "EventQueue",
    "WorkflowEvent",
    "AgentFn",
    "EdgeCondition",
    "slice_state",
    "StateStore",
    "InMemoryStore",
    "SQLiteStore",
    "PostgreSQLStore",
    # coordination
    "ConflictResolver",
    "LastWriteWins",
    "PriorityBased",
    "RejectIncoming",
    "InvariantChecker",
    "InvariantViolation",
    "BatchResolutionResult",
    "Checkpoint",
    "load_latest_checkpoint",
    "save_checkpoint",
    "ReplayDebugger",
    "replay",
    "__version__",
]
