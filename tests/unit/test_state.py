import pytest
from pydantic import ValidationError

from agentstate.core.state import SharedState, Task

def test_shared_state_defaults():
    state = SharedState(goal="test_goal")
    assert isinstance(state.workflow_id, str)
    assert state.workflow_id != ""
    assert state.tasks == {}
    assert state.artifacts == {}
    assert state.status == "running"


def test_shared_state_validation_rejects_invalid_status():
    with pytest.raises(ValidationError):
        SharedState(goal="x", status="invalid_status")

def test_task_defaults():
    task = Task(description="do something")
    assert task.status == "pending"
    assert task.result is None
    assert isinstance(task.id, str)
    assert task.id != ""

def test_two_states_have_different_ids():
    state1 = SharedState(goal="same goal")
    state2 = SharedState(goal="same goal")
    assert state1.workflow_id != state2.workflow_id

