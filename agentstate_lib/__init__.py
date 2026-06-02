from __future__ import annotations

from agentstate_lib.core.events import (
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
from agentstate_lib.core.patch import (
    StatePatch,
    apply_patch,
    get_nested,
    set_nested,
)
from agentstate_lib.core.state import (
    Artifact,
    Decision,
    Goal,
    SharedState,
    Task,
    WorkflowStatus,
)
from agentstate_lib.memory.store import InMemoryStore, SQLiteStore, StateStore
from agentstate_lib.router.context import slice_state
from agentstate_lib.router.graph import AgentGraph
from agentstate_lib.router.types import AgentFn, EdgeCondition

__version__ = "0.1.0"

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
    "AgentFn",
    "EdgeCondition",
    "slice_state",
    "StateStore",
    "InMemoryStore",
    "SQLiteStore",
    "__version__",
]