from __future__ import annotations

import pytest

from agentstatelib.coordination import (
    CompletedGoalsHaveNoBlockingTasks,
    InvariantChecker,
    InvariantViolation,
    TasksReferenceExistingGoals,
    check_all,
)
from agentstatelib.core.patch import StatePatch, apply_patch
from agentstatelib.core.state import SharedState


def test_no_violations_on_clean_state() -> None:
    state = SharedState(goal="test")
    # No goals, no tasks: nothing should violate TasksReferenceExistingGoals
    violations = check_all(state, [TasksReferenceExistingGoals()])
    assert violations == []


def test_detects_task_with_missing_goal() -> None:
    state = SharedState(goal="test")

    # Add a task with goal_id that doesn't exist
    patch = StatePatch(
        agent_id="tester",
        target="tasks.t1",
        value={
            "description": "do something",
            "status": "pending",
            "goal_id": "nonexistent_goal_id",
        },
        reason="add bad task",
    )
    state = apply_patch(state, patch)

    violations = check_all(state, [TasksReferenceExistingGoals()])
    assert len(violations) >= 1


def test_custom_invariant_checker() -> None:
    class AlwaysViolates:
        def check(self, state: SharedState) -> list[InvariantViolation]:
            return [
                InvariantViolation(
                    rule_name="AlwaysViolates",
                    description="This checker always returns one violation.",
                    severity="error",
                )
            ]

    state = SharedState(goal="test")
    violations = check_all(state, [AlwaysViolates()])
    assert any(v.rule_name == "AlwaysViolates" for v in violations)


def test_multiple_checkers_all_run() -> None:
    state = SharedState(goal="test")

    # Goal g1 is complete
    goal_patch = StatePatch(
        agent_id="tester",
        target="goals.g1",
        value={
            "description": "test goal",
            "status": "complete",
        },
        reason="add complete goal",
    )
    state = apply_patch(state, goal_patch)

    # Task t1 refers to missing goal_id "ghost"
    bad_task_patch = StatePatch(
        agent_id="tester",
        target="tasks.t1",
        value={
            "description": "bad task",
            "status": "pending",
            "goal_id": "ghost",
        },
        reason="add bad task",
    )
    state = apply_patch(state, bad_task_patch)

    # Task t2 blocks completed goal g1
    blocking_task_patch = StatePatch(
        agent_id="tester",
        target="tasks.t2",
        value={
            "description": "blocking task",
            "status": "pending",
            "goal_id": "g1",
        },
        reason="add blocking task",
    )
    state = apply_patch(state, blocking_task_patch)

    violations = check_all(
        state, [TasksReferenceExistingGoals(), CompletedGoalsHaveNoBlockingTasks()]
    )
    # At least: one for missing goal_id "ghost", one for blocking task on g1
    assert len(violations) >= 2


def test_task_with_none_goal_id_is_not_a_violation() -> None:
    state = SharedState(goal="test")

    patch = StatePatch(
        agent_id="tester",
        target="tasks.t1",
        value={
            "description": "do something",
            "goal_id": None,
            "status": "pending",
        },
        reason="add ungrouped task",
    )

    state = apply_patch(state, patch)

    violations = check_all(
        state,
        [TasksReferenceExistingGoals()],
    )

    assert violations == []


def test_invariant_handles_dict_tasks() -> None:
    state = SharedState(goal="test")

    patch = StatePatch(
        agent_id="tester",
        target="tasks.t1",
        value={
            "description": "dict task",
            "goal_id": None,
            "status": "pending",
        },
        reason="add dict task",
    )

    state = apply_patch(state, patch)

    try:
        violations = check_all(
            state,
            [
                TasksReferenceExistingGoals(),
                CompletedGoalsHaveNoBlockingTasks(),
            ],
        )
    except AttributeError as exc:
        pytest.fail(f"Dict-backed tasks should not raise AttributeError: {exc}")

    assert isinstance(violations, list)
