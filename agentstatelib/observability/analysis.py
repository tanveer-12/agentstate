from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from agentstatelib.core.events import (
    AgentErrored,
    ConflictDetected,
    ModelCalled,
    ModelReturned,
    PatchApplied,
    RetryAttempted,
    StateEvent,
    ValidationFailed,
    WorkflowCompleted,
    WorkflowStarted,
)
from agentstatelib.memory.replay import get_model_call_pairs


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

    total_model_calls: int = 0
    total_validation_failures: int = 0
    total_retries: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_total_cost_usd: float | None = None
    avg_model_latency_seconds: float | None = None
    models_used: list[str] = Field(default_factory=list)


def analyze_workflow(events: list[StateEvent]) -> WorkflowSummary:
    start_time: float | None = None
    end_time: float | None = None
    workflow_id = events[0].workflow_id if events else ""
    total_patches = 0
    total_conflicts = 0
    agent_stats: dict[str, AgentStats] = {}
    flags: list[AnomalyFlag] = []

    model_calls = [e for e in events if isinstance(e, ModelCalled)]
    model_returns = [e for e in events if isinstance(e, ModelReturned)]
    validation_failures = [e for e in events if isinstance(e, ValidationFailed)]
    retries = [e for e in events if isinstance(e, RetryAttempted)]

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

    total_model_calls = len(model_calls)
    total_validation_failures = len(validation_failures)
    total_retries = len(retries)
    total_input_tokens = sum(e.input_tokens or 0 for e in model_returns)
    total_output_tokens = sum(e.output_tokens or 0 for e in model_returns)

    costs = [
        e.estimated_cost_usd for e in model_returns if e.estimated_cost_usd is not None
    ]
    estimated_total_cost_usd = sum(costs) if costs else None

    call_pairs = get_model_call_pairs(events)
    avg_model_latency_seconds = (
        sum(returned.latency_seconds for _, returned in call_pairs) / len(call_pairs)
        if call_pairs
        else None
    )

    models_used = sorted({e.model for e in model_calls})

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

    if total_model_calls and total_retries > total_model_calls * 0.3:
        flags.append(
            AnomalyFlag(
                rule_name="high_retry_rate",
                description="high retry rate, consider grammar-constrained output",
                severity="warning",
            )
        )

    if estimated_total_cost_usd is not None and estimated_total_cost_usd > 1.0:
        flags.append(
            AnomalyFlag(
                rule_name="high_cost",
                description=f"Estimated cost ${estimated_total_cost_usd:.2f} exceeds $1.00",
                severity="warning",
            )
        )

    if any(v.error_type == "schema_validation_error" for v in validation_failures):
        flags.append(
            AnomalyFlag(
                rule_name="schema_drift",
                description="schema drift detected in validation failures",
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
        total_model_calls=total_model_calls,
        total_validation_failures=total_validation_failures,
        total_retries=total_retries,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        estimated_total_cost_usd=estimated_total_cost_usd,
        avg_model_latency_seconds=avg_model_latency_seconds,
        models_used=models_used,
    )
