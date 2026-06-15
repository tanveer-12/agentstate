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
    ContextSliced,
    HumanApprovalRequested,
    HumanApprovalResolved,
    ModelCalled,
    ModelReturned,
    PatchApplied,
    PromptAssembled,
    RetryAttempted,
    StateEvent,
    ToolCalled,
    ToolReturned,
    ValidationFailed,
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
from agentstatelib.memory.replay import (
    AgentTurn,
    ReplayDebugger,
    get_agent_turns,
    get_model_call_pairs,
    get_turn_for_patch,
    replay,
)
from agentstatelib.memory.store import (
    InMemoryStore,
    PostgreSQLStore,
    SQLiteStore,
    StateStore,
)
from agentstatelib.observability.analysis import (
    AgentStats,
    AnomalyFlag,
    WorkflowSummary,
    analyze_workflow,
)
from agentstatelib.observability.dashboard import WorkflowDashboard
from agentstatelib.observability.tracing import get_tracer, setup_tracing
from agentstatelib.router.context import slice_state
from agentstatelib.router.graph import AgentGraph, EventQueue, WorkflowEvent
from agentstatelib.router.types import AgentFn, EdgeCondition

__version__ = "0.5.0"

__all__ = [
    # core state
    "SharedState",
    "Task",
    "Goal",
    "Artifact",
    "Decision",
    "WorkflowStatus",
    # patches
    "StatePatch",
    "apply_patch",
    "set_nested",
    "get_nested",
    # events — base + phase 1
    "StateEvent",
    "BaseStateEvent",
    "WorkflowStarted",
    "WorkflowCompleted",
    "PatchApplied",
    "ConflictDetected",
    "CheckpointSaved",
    "AgentErrored",
    "event_adapter",
    # events — phase 2A trace
    "ContextSliced",
    "PromptAssembled",
    "ModelCalled",
    "ModelReturned",
    "ValidationFailed",
    "RetryAttempted",
    "ToolCalled",
    "ToolReturned",
    # events — phase 2E approval
    "HumanApprovalRequested",
    "HumanApprovalResolved",
    # graph
    "AgentGraph",
    "EventQueue",
    "WorkflowEvent",
    "AgentFn",
    "EdgeCondition",
    "slice_state",
    # persistence
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
    # checkpointing
    "Checkpoint",
    "load_latest_checkpoint",
    "save_checkpoint",
    # replay
    "ReplayDebugger",
    "replay",
    "AgentTurn",
    "get_agent_turns",
    "get_model_call_pairs",
    "get_turn_for_patch",
    # observability
    "WorkflowDashboard",
    "analyze_workflow",
    "WorkflowSummary",
    "AnomalyFlag",
    "AgentStats",
    "setup_tracing",
    "get_tracer",
    # version
    "__version__",
]
