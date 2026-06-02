from __future__ import annotations

from agentstatelib.core.patch import(
    StatePatch,
    apply_patch,
    get_nested,
    set_nested,
)

from agentstatelib.core.state import SharedState, Task

def test_set_nested_simple() -> None:
    result = set_nested({}, "a", "value")
    assert result == {"a": "value"}

def test_set_nested_deep_path() -> None:
    result = set_nested({}, "a.b.c", 42)
    assert result["a"]["b"]["c"] == 42

def test_set_nested_creates_intermediate_dicts() -> None:
    result = set_nested({}, "tasks.task_1.status", "done")
    assert result["tasks"]["task_1"]["status"] == "done"

def test_get_nested_returns_none_for_missing_path() -> None:
    result = get_nested({}, "a.b.c")
    assert result is None

def test_apply_patch_returns_new_state() -> None:
    state = SharedState(goal="test")
    patch = StatePatch(
        agent_id="a",
        target="facts.key",
        value="val",
        reason="test",
    )
    new_state = apply_patch(state, patch)
    assert new_state is not state
    assert state.facts == {}
    assert new_state.facts.get("key") == "val"

def test_apply_patch_deep_target() -> None:
    state = SharedState(goal="test")
    # create a task with required fields
    task = Task(description="dummy task")
    state.tasks["t1"] = task

    patch = StatePatch(
        agent_id="a",
        target="tasks.t1.status",
        value="done",
        reason="test",
    )

    new_state = apply_patch(state, patch)

    assert new_state.tasks["t1"].status == "done"