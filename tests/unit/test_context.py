from __future__ import annotations

from agentstate_lib.core.patch import StatePatch, apply_patch
from agentstate_lib.core.state import SharedState
from agentstate_lib.router.context import slice_state

def test_slice_state_returns_only_requested_paths() -> None:
    state = SharedState(goal="test")
    patch = StatePatch(
        agent_id="a",
        target="facts.key",
        value="value",
        reason="test",
    )
    state = apply_patch(state, patch)
    result = slice_state(state, ["goal"])

    assert "goal" in result
    assert "tasks" not in result
    assert "artifacts" not in result

def test_slice_state_handles_nested_paths() -> None:
    state = SharedState(goal="test")
    patch1 = StatePatch(
        agent_id="a",
        target="facts.key1",
        value="value1",
        reason="test1",
    )
    patch2 = StatePatch(
        agent_id="a",
        target="facts.key2",
        value="value2",
        reason="test2",
    )
    state = apply_patch(state, patch1)
    state = apply_patch(state, patch2)

    result = slice_state(state, ["facts.key1"])
    assert result["facts"]["key1"] == "value1"
    assert "key2" not in result.get("facts", {})

def test_slice_state_empty_include_returns_full_state() -> None:
    state = SharedState(goal="test")

    result = slice_state(state, [])

    assert "goal" in result
    assert "tasks" in result
    assert "artifacts" in result