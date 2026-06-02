import pytest
from pydantic import ValidationError

from agentstatelib.core.events import (
    AgentErrored,
    BaseStateEvent,
    CheckpointSaved,
    ConflictDetected,
    PatchApplied,
    WorkflowStarted,
    WorkflowCompleted,
    event_adapter
)

def test_patch_applied_event_round_trip():
    original = PatchApplied(
        workflow_id="wf-1",
        agent_id="agent-1",
        type="patch_applied",
        patch_id="patch-1",
        target="goal",
        old_value="old",
        new_value="new",
        reason="update goal",
    )
    json_string = original.model_dump_json()
    result = event_adapter.validate_json(json_string)
    assert isinstance(result, PatchApplied)
    assert result.patch_id == original.patch_id


def test_discriminated_union_selects_correct_types():
    original = WorkflowStarted(
        workflow_id="wf-1",
        agent_id="agent-1",
        type="workflow_started",
        workflow_type="general",
        goal="write report",
    )
    json_string = original.model_dump_json()
    result = event_adapter.validate_json(json_string)
    assert isinstance(result, WorkflowStarted)
    assert not isinstance(result, PatchApplied)

def test_all_event_types_serialize():
    events = [
        WorkflowStarted(
            workflow_id="wf-1",
            agent_id="agent-1",
            type="workflow_started",
            workflow_type="general",
            goal="write report",
        ),
        WorkflowCompleted(
            workflow_id="wf-1",
            agent_id="agent-1",
            type="workflow_completed",
            final_status="complete",
        ),
        PatchApplied(
            workflow_id="wf-1",
            agent_id="agent-1",
            type="patch_applied",
            patch_id="patch-1",
            target="goal",
            old_value="old",
            new_value="new",
            reason="update goal",
        ),
        ConflictDetected(
            workflow_id="wf-1",
            agent_id="agent-1",
            type="conflict_detected",
            conflict_id="conflict-1",
            path="goal",
            winner_agent_id="agent-1",
            loser_agent_id="agent-2",
            resolution_strategy="last_write_wins",
        ),
        CheckpointSaved(
            workflow_id="wf-1",
            agent_id="agent-1",
            type="checkpoint_saved",
            checkpoint_id="checkpoint-1",
            event_count=3,
        ),
        AgentErrored(
            workflow_id="wf-1",
            agent_id="agent-1",
            type="agent_errored",
            error_type="ValueError",
            error_message="bad value",
            retry_count=1,
        ),
    ]
    for event in events:
        json_string = event.model_dump_json()
        result = event_adapter.validate_json(json_string)
        assert result.event_id == event.event_id

def test_base_fields_present_on_all_events():
    events = [
        WorkflowStarted(
            workflow_id="wf-1",
            agent_id="agent-1",
            type="workflow_started",
            workflow_type="general",
            goal="write report",
        ),
        WorkflowCompleted(
            workflow_id="wf-1",
            agent_id="agent-1",
            type="workflow_completed",
            final_status="complete",
        ),
        PatchApplied(
            workflow_id="wf-1",
            agent_id="agent-1",
            type="patch_applied",
            patch_id="patch-1",
            target="goal",
            old_value="old",
            new_value="new",
            reason="update goal",
        ),
        ConflictDetected(
            workflow_id="wf-1",
            agent_id="agent-1",
            type="conflict_detected",
            conflict_id="conflict-1",
            path="goal",
            winner_agent_id="agent-1",
            loser_agent_id="agent-2",
            resolution_strategy="last_write_wins",
        ),
        CheckpointSaved(
            workflow_id="wf-1",
            agent_id="agent-1",
            type="checkpoint_saved",
            checkpoint_id="checkpoint-1",
            event_count=3,
        ),
        AgentErrored(
            workflow_id="wf-1",
            agent_id="agent-1",
            type="agent_errored",
            error_type="ValueError",
            error_message="bad value",
            retry_count=1,
        ),
    ]
    for event in events:
        assert hasattr(event, "event_id")
        assert hasattr(event, "workflow_id")
        assert hasattr(event, "agent_id")
        assert hasattr(event, "timestamp")


def test_invalid_type_field_raises():
    with pytest.raises(ValidationError):
        event_adapter.validate_json(
            '{"type": "nonexistent", "workflow_id":"x", "agent_id":"y"}'
        )