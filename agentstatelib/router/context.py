from __future__ import annotations

from typing import Any

from agentstatelib.core.patch import get_nested, set_nested
from agentstatelib.core.state import SharedState


def slice_state(state: SharedState, include_paths: list[str]) -> dict[str, Any]:
    """
    Extract a subset of SharedState by dotted path.

    Each agent node declares which paths it needs via the
    context= parameter of @graph.node().

    The agent receives exactly those paths — nothing more.
    The returned dict always includes workflow_id, workflow_type,
    and goal so agents can identify the workflow without needing
    to explicitly list those paths.

    This serves two purposes:

    1. Limits context window usage for LLM-backed agents.
    2. Prevents agents from accidentally reading state they
    should not see.
    """
    full_dict = state.model_dump()
    base: dict[str, Any] = {
        "workflow_id": state.workflow_id,
        "workflow_type": state.workflow_type,
        "goal": state.goal,
    }

    if not include_paths:
        base.update(full_dict)
        return base

    result: dict[str, Any] = dict(base)
    for path in include_paths:
        value = get_nested(full_dict, path)
        if value is not None:
            set_nested(result, path, value)

    return result
