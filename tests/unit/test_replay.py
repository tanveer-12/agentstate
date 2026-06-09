import pytest

from agentstatelib.core.events import PatchApplied, StateEvent, WorkflowStarted
from agentstatelib.core.patch import StatePatch
from agentstatelib.memory.replay import ReplayDebugger, replay


def _workflow_started() -> WorkflowStarted:
    return WorkflowStarted(
        workflow_id="wf-1",
        agent_id="system",
        workflow_type="test",
        goal="test goal",
        timestamp=1.0,
    )


def _patch_event(
    target: str,
    value: object,
    timestamp: float,
    patch_id: str,
) -> PatchApplied:
    patch = StatePatch(
        agent_id="agent-1",
        target=target,
        value=value,
        reason="test",
        patch_id=patch_id,
    )
    return PatchApplied(
        workflow_id="wf-1",
        agent_id=patch.agent_id,
        target=patch.target,
        old_value=None,
        new_value=patch.value,
        reason=patch.reason,
        patch_id=patch.patch_id,
        timestamp=timestamp,
    )


def test_replay_reconstructs_state() -> None:
    events: list[StateEvent] = [
        _workflow_started(),
        _patch_event("facts.a", 1, 2.0, "patch-1"),
        _patch_event("facts.b", 2, 3.0, "patch-2"),
    ]

    state = replay(events)

    assert state.facts.get("a") == 1
    assert state.facts.get("b") == 2


def test_replay_missing_workflow_started_raises() -> None:
    patch_event = _patch_event("facts.a", 1, 1.0, "patch-1")

    with pytest.raises(ValueError):
        replay([patch_event])


def test_debugger_step_advances_cursor() -> None:
    events = [
        _workflow_started(),
        _patch_event("facts.a", 1, 2.0, "patch-1"),
        _patch_event("facts.b", 2, 3.0, "patch-2"),
    ]
    debugger = ReplayDebugger(events)

    debugger.step()
    debugger.step()

    assert debugger.current_index == 2


def test_debugger_jump_to_index() -> None:
    events = [
        _workflow_started(),
        _patch_event("facts.a", 1, 2.0, "patch-1"),
        _patch_event("facts.b", 2, 3.0, "patch-2"),
        _patch_event("facts.c", 3, 4.0, "patch-3"),
        _patch_event("facts.d", 4, 5.0, "patch-4"),
    ]
    debugger = ReplayDebugger(events)

    state = debugger.jump_to(3)

    assert state.facts.get("a") == 1
    assert state.facts.get("b") == 2
    assert state.facts.get("c") == 3
    assert state.facts.get("d") is None


def test_debugger_stop_iteration_at_end() -> None:
    events: list[StateEvent] = [_workflow_started()]
    debugger = ReplayDebugger(events)

    debugger.step()

    with pytest.raises(StopIteration):
        debugger.step()
