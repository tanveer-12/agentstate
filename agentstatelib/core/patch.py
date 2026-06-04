from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from agentstatelib.core.state import SharedState


# represents "one change an agent wants to make" to the shared state
class StatePatch(BaseModel):
    """
    A structured state update proposal returned by an agent.

    Agents never write to SharedState directly — they return a
    StatePatch. The library validates the patch, resolves conflicts
    with other patches from the same round, applies the winner to
    state, and logs a PatchApplied event.

    The reason field is required for a meaningful audit trail.
    """

    patch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    target: str  # dotted path, eg: tasks.task_1.status
    value: Any
    reason: str
    timestamp: float = Field(default_factory=time.time)
    priority: int = 0


def set_nested(obj: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    """
    Set a value at a dotted path inside a nested dictionary.

    Example:
        set_nested({}, "tasks.t1.status", "done")

    Produces:

        {
            "tasks": {
                "t1": {
                    "status": "done"
                }
            }
        }
    """
    parts = path.split(".")  # turns "a.b.c" into ["a","b","c"]
    current = obj

    for key in parts[:-1]:
        child = current.get(key)
        if not isinstance(child, dict):
            child = {}
            current[key] = child
        current = child

    current[parts[-1]] = value
    return obj


def get_nested(obj: dict[str, Any], path: str) -> Any:
    """
    Retrieve a value from a nested dictionary using a dotted path.

    Example:

        get_nested(
            {"tasks": {"t1": {"status": "done"}}},
            "tasks.t1.status"
        )

    returns:

        "done"

    get_nested({}, "a.b.c") returns None.
    """

    parts = path.split(".")
    current: Any = obj

    for key in parts:
        if not isinstance(current, dict):
            return None
        if key not in current:
            return None
        current = current[key]

    return current


# creates a dict view of SharedState with model_dump()
def apply_patch(state: SharedState, patch: StatePatch) -> SharedState:
    """Apply a StatePatch to a SharedState, returning a new SharedState.

    The original state object is never modified. This immutability is
    what makes event replay and conflict detection possible — any
    previous state can be reconstructed.
    """
    from agentstatelib.core.state import SharedState

    state_dict = state.model_dump()
    set_nested(state_dict, patch.target, patch.value)
    return SharedState.model_validate(state_dict)
