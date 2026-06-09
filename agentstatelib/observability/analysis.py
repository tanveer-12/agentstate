from typing import Any, Literal

from pydantic import BaseModel, Field

from agentstatelib.core.events import (
    AgentErrored,
    ConflictDetected,
    PatchApplied,
    StateEvent,
    WorkflowCompleted,
    WorkflowStarted,
)


class AnomalyFlag(BaseModel):
    """
    A flag raised by an anomaly detection rule.
    warning severity is informational.
    error severity indicates a workflow that should be investigated.
    """

    rule_name: str
    description: str
    severity: Literal["warning", "error"]


class AgentStats(BaseModel):
    """
    Aggregated statistics for one agent across a workflow run.
    """

    agent_id: str
    patch_count: int = 0
    error_count: int = 0


class WorkflowSummary(BaseModel):
    """Statistics for a completed workflow run derived from the event log. Use analyze_workflow() to compute."""

    workflow_id: str
    total_duration_seconds: float
    total_patches: int
    total_conflicts: int
    conflict_rate: float
    agent_stats: dict[str, AgentStats] = Field(default_factory=dict)
    is_anomalous: bool = False
    anomaly_flags: list[AnomalyFlag] = Field(default_factory=list)


def analyze_workflow(events: list[StateEvent]) -> WorkflowSummary:
    start_time: float | None = None
    end_time: float | None = None
    workflow_id = events[0].workflow_id if events else ""
    total_patches = 0
    total_conflicts = 0
    agent_stats: dict[str, AgentStats] = {}
    flags: list[AnomalyFlag] = []

    for event in events:
        if start_time is None and isinstance(event, WorkflowStarted):
            start_time = event.timestamp
            workflow_id = event.workflow_id
        if isinstance(event, WorkflowCompleted) and end_time is None:
            end_time = event.timestamp
            workflow_id = event.workflow_id
        if isinstance(event, PatchApplied):
            total_patches += 1
            stats = agent_stats.setdefault(
                event.agent_id, AgentStats(agent_id=event.agent_id)
            )
            stats.patch_count += 1
        if isinstance(event, AgentErrored):
            stats = agent_stats.setdefault(
                event.agent_id, AgentStats(agent_id=event.agent_id)
            )
            stats.error_count += 1
        if isinstance(event, ConflictDetected):
            total_conflicts += 1

    if start_time is None:
        start_time = events[0].timestamp if events else 0.0
    if end_time is None:
        end_time = events[-1].timestamp if events else start_time

    total_duration_seconds = end_time - start_time
    conflict_rate = total_conflicts / max(total_patches, 1)

    if conflict_rate > 0.2:
        flags.append(
            AnomalyFlag(
                rule_name="high_conflict_rate",
                description=f"Conflict rate {conflict_rate:.1%} exceeds 20%",
                severity="warning",
            )
        )
    if total_duration_seconds > 300:
        flags.append(
            AnomalyFlag(
                rule_name="long_duration",
                description=f"Workflow duration {total_duration_seconds:.1f}s exceeds 300s",
                severity="warning",
            )
        )
    for stats in agent_stats.values():
        if stats.patch_count == 0:
            flags.append(
                AnomalyFlag(
                    rule_name="dead_agent",
                    description=f"Agent {stats.agent_id} produced no patches — possible dead agent",
                    severity="warning",
                )
            )

    return WorkflowSummary(
        workflow_id=workflow_id,
        total_duration_seconds=total_duration_seconds,
        total_patches=total_patches,
        total_conflicts=total_conflicts,
        conflict_rate=conflict_rate,
        agent_stats=agent_stats,
        is_anomalous=any(f.severity == "error" for f in flags),
        anomaly_flags=flags,
    )
