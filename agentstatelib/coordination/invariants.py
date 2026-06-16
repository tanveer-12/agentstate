from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from agentstatelib.core.state import SharedState


class InvariantViolation(BaseModel):
    """
    A single violation emitted by an InvariantChecker.
    severity="error" -> AgentGraph.run() raises RuntimeError
    and halts.
    severity="warning" -> Logged but does not halt the workflow
    """

    rule_name: str
    description: str
    severity: Literal["warning", "error"] = Field(default="error")


@runtime_checkable
class InvariantChecker(Protocol):
    def check(self, state: SharedState) -> list[InvariantViolation]:
        """
        Inspect the current SharedState and return any invariant violations
        """
        ...


def _get_task_field(task: object, field: str, default: object = None) -> object:
    """
    Safely read a field from a task that maybe a Task model or a plain dict
    """
    if isinstance(task, dict):
        return task.get(field, default)
    return getattr(task, field, default)


class TasksReferenceExistingGoals:
    """
    Every task whose goal_id is set must reference a goal that exists.

    Tasks with goal_id=None are ungrouped tasks — valid in workflows that
    do not use the goal hierarchy. They are skipped without a violation.
    """

    def check(self, state: SharedState) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []

        # Assume state.tasks is a dict-like mapping task_id->task
        for task_id, task in state.tasks.items():
            goal_id = _get_task_field(task, "goal_id")
            status = _get_task_field(task, "status", "pending")

            # ungrouped tasks are allowed - skip them
            if goal_id is None:
                continue

            if goal_id not in state.goals:
                violations.append(
                    InvariantViolation(
                        rule_name="TasksReferenceExistingGoals",
                        description=(
                            f"Task '{task_id}' (status={status}) references "
                            f"goal_id '{goal_id}' which does not exist in state.goals"
                        ),
                        severity="error",
                    )
                )
        return violations


class CompletedGoalsHaveNoBlockingTasks:
    """
    A goal marked 'complete' must have no tasks still pending or running.
    If a goal is complete but tasks that belong to it are still in-progress,
    the workflow state is internally inconsistent.
    """

    def check(self, state: SharedState) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []

        for goal_id, goal in state.goals.items():
            goal_status = _get_task_field(goal, "status", "pending")
            if goal_status != "complete":
                continue

            blocking_tasks: list[str] = []
            for task_id, task in state.tasks.items():
                task_goal_id = _get_task_field(task, "goal_id")
                task_status = _get_task_field(task, "status", "pending")

                if task_goal_id == goal_id and task_status in {
                    "pending",
                    "running",
                }:
                    blocking_tasks.append(task_id)

            if blocking_tasks:
                violations.append(
                    InvariantViolation(
                        rule_name="CompletedGoalsHaveNoBlockingTasks",
                        description=(
                            f"Goal '{goal_id}' is marked complete but has  "
                            f"blocking tasks still in progress: "
                            f"{', '.join(blocking_tasks)}."
                        ),
                        severity="error",
                    )
                )
        return violations


def check_all(
    state: SharedState,
    checkers: list[InvariantChecker],
) -> list[InvariantViolation]:
    """
    Run all checkers against state and return every violation found.
    Checkers run in order. All checkers always run - a violation from
    one checker does not prevent the rest from running.
    """
    violations: list[InvariantViolation] = []
    for checker in checkers:
        violations.extend(checker.check(state))
    return violations
