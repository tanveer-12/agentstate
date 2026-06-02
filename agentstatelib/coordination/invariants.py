from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from agentstatelib.core.state import SharedState


class InvariantViolation(BaseModel):
    rule_name: str
    description: str
    severity : Literal["warning", "error"] = Field(default="error")


@runtime_checkable
class InvariantChecker(Protocol):
    def check(self, state: SharedState) -> list[InvariantViolation]:
        """
        Inspect the current SharedState and return any invariant violations
        """
        ...


class TasksReferenceExistingGoals:
    def check(self, state: SharedState) -> list[InvariantViolation]:
        violations : list[InvariantViolation] = []

        # Assume state.tasks is a dict-like mapping task_id->task
        for task_id, task in state.tasks.items():
            goal_id = getattr(task, "goal_id", None)
            if goal_id is None:
                # for now, ignore tasks with no goal_id; you can tighten this later
                continue

            if goal_id not in state.goals:
                violations.append(
                    InvariantViolation(
                        rule_name="TasksReferenceExistingGoals",
                        description=(
                            f"Task '{task_id}' (status={task.status}) "
                            f"references missing goal_id '{goal_id}'."
                        ),
                        severity="error",
                    )
                )
        return violations
    
class CompletedGoalsHaveNoBlockingTasks:
    def check(self, state: SharedState) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []

        # state.goals: dict[str, Goal]
        for goal_id, goal in state.goals.items():
            if goal.status != "complete":
                continue

            blocking_tasks: list[str] = []
            for task_id, task in state.tasks.items():
                goal_id_for_task = getattr(task, "goal_id", None)
                if goal_id_for_task == goal_id and task.status in {
                    "pending", 
                    "running"
                }:
                    blocking_tasks.append(task_id)
                
            if blocking_tasks:
                violations.append(InvariantViolation(
                        rule_name="CompletedGoalsHaveNoBlockingTasks",
                        description=(
                            f"Goal '{goal_id}' is complete but has blocking tasks: "
                            f"{', '.join(blocking_tasks)}."
                        ),
                        severity="error",
                    )
                )
        return violations
        

def check_all(
        state: SharedState, 
        checkers: list[InvariantChecker]
    ) -> list[InvariantViolation]:
    violations: list[InvariantViolation] = []
    for checker in checkers:
        violations.extend(checker.check(state))
    return violations