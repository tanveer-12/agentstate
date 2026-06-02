from __future__ import annotations

from typing import Any

from agentstatelib.core.patch import get_nested, set_nested
from agentstatelib.core.state import SharedState


def slice_state(state: SharedState, include_paths: list[str]) -> dict[str, Any]:
    """
    Returns a dict view of just the requested paths from SharedState.
    if include_paths is empty, return the full state dict
    """
    full_dict = state.model_dump()
    # no slice requested mean "full context"
    if not include_paths:
        return full_dict
    
    result : dict[str, Any]  = {}
    for path in include_paths:
        value = get_nested(full_dict, path)
        if value is not None:
            set_nested(result, path, value)
    return result
