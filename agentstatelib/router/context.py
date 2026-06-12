from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from pydantic import BaseModel, Field

from agentstatelib.core.patch import get_nested, set_nested
from agentstatelib.core.state import SharedState


class ContextSlice(BaseModel):
    workflow_id: str
    workflow_type: str
    goal: str
    data: dict[str, Any] = Field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        if key == "workflow_id":
            return self.workflow_id
        if key == "workflow_type":
            return self.workflow_type
        if key == "goal":
            return self.goal
        return self.data[key]

    def __contains__(self, key: str) -> bool:
        if key in {"workflow_id", "workflow_type", "goal"}:
            return True
        return key in self.data

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


def slice_state(state: SharedState, include_paths: list[str]) -> ContextSlice:
    """
    Extract a subset of SharedState by dotted path.

    Each agent node declares which paths it needs via the
    context= parameter of @graph.node().

    The agent receives exactly those paths — nothing more.

    This serves two purposes:

    1. Limits context window usage for LLM-backed agents.
    2. Prevents agents from accidentally reading state they
    should not see.
    """
    full_dict = state.model_dump()
    if not include_paths:
        return ContextSlice(
            workflow_id=state.workflow_id,
            workflow_type=state.workflow_type,
            goal=state.goal,
            data=full_dict,
        )

    result: dict[str, Any] = {}
    for path in include_paths:
        value = get_nested(full_dict, path)
        if value is not None:
            set_nested(result, path, value)

    return ContextSlice(
        workflow_id=state.workflow_id,
        workflow_type=state.workflow_type,
        goal=state.goal,
        data=result,
    )
