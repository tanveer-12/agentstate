from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from agentstatelib.core.state import SharedState


# represents "one change an agent wants to make" to the shared state
class StatePatch(BaseModel):
    patch_id:str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    target : str # dotted path, eg: tasks.task_1.status
    value : Any
    reason : str
    timestamp : float = Field(default_factory=time.time)
    priority : int = 0

def set_nested(obj: dict[str, Any], path: str, value : Any) -> dict[str, Any]:
    """
    Set value at a dotted path inside a nested dict, creating dicts as needed.
    """
    parts = path.split(".") # turns "a.b.c" into ["a","b","c"]
    current : dict[str, Any] = obj

    for key in parts[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    
    current[parts[-1]] = value
    return obj

def get_nested(obj: dict[str, Any], path: str) -> Any:
    """
    Get value at a dotted path from a nested dict, or None if missing.
    """

    parts = path.split(".")
    current : Any = obj

    for key in parts:
        if not isinstance(current, dict):
            return None
        if key not in current:
            return None
        current = current[key]
    
    return current

# creates a dict view of SharedState with model_dump()
def apply_patch(state: SharedState, patch: StatePatch) -> SharedState:
    """Return a new SharedState with the patch applied at patch.target"""
    state_dict = state.model_dump()
    set_nested(state_dict, patch.target, patch.value)
    return SharedState.model_validate(state_dict)