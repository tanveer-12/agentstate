import pytest

from agentstatelib.core.events import (
    ContextSliced,
    ModelCalled,
    ModelReturned,
    PatchApplied,
    PromptAssembled,
    RetryAttempted,
    StateEvent,
    ValidationFailed,
    WorkflowStarted,
)
from agentstatelib.core.patch import StatePatch
from agentstatelib.memory.replay import (
    ReplayDebugger,
    get_agent_turns,
    get_model_call_pairs,
    get_turn_for_patch,
    replay,
)


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


def test_get_model_call_pairs_pairs_by_call_id() -> None:
    call_id = "call-1"
    events = [
        ModelCalled(
            workflow_id="wf-1",
            agent_id="agent-1",
            model="llama3:8b",
            provider="ollama",
            attempt_number=0,
            call_id=call_id,
        ),
        ModelReturned(
            workflow_id="wf-1",
            agent_id="agent-1",
            call_id=call_id,
            raw_response='{"target":"facts.x","value":"ok","reason":"done"}',
            latency_seconds=1.25,
            input_tokens=10,
            output_tokens=5,
            estimated_cost_usd=0.01,
        ),
    ]

    pairs = get_model_call_pairs(events)

    assert len(pairs) == 1
    called, returned = pairs[0]
    assert called.call_id == call_id
    assert returned.call_id == call_id
    assert returned.latency_seconds == pytest.approx(1.25)


def test_get_agent_turns_groups_single_successful_turn() -> None:
    call_id = "call-1"
    patch_id = "patch-1"
    events = [
        WorkflowStarted(
            workflow_id="wf-1",
            agent_id="system",
            workflow_type="test",
            goal="test goal",
            timestamp=1.0,
        ),
        ContextSliced(
            workflow_id="wf-1",
            agent_id="agent-1",
            context_paths=["goal", "facts"],
            context_size_bytes=128,
            snapshot_workflow_id="wf-1",
        ),
        PromptAssembled(
            workflow_id="wf-1",
            agent_id="agent-1",
            prompt_text="prompt",
            system_prompt_length=12,
            context_length=34,
            is_correction_attempt=False,
            attempt_number=0,
        ),
        ModelCalled(
            workflow_id="wf-1",
            agent_id="agent-1",
            model="llama3:8b",
            provider="ollama",
            attempt_number=0,
            call_id=call_id,
        ),
        ModelReturned(
            workflow_id="wf-1",
            agent_id="agent-1",
            call_id=call_id,
            raw_response='{"target":"facts.x","value":"ok","reason":"done"}',
            latency_seconds=1.25,
            input_tokens=10,
            output_tokens=5,
            estimated_cost_usd=0.01,
        ),
        ValidationFailed(
            workflow_id="wf-1",
            agent_id="agent-1",
            attempt_number=0,
            error_type="json_decode_error",
            error_message="bad json",
            raw_output="not json",
            will_retry=True,
        ),
        RetryAttempted(
            workflow_id="wf-1",
            agent_id="agent-1",
            attempt_number=1,
            previous_error="bad json",
        ),
        PatchApplied(
            workflow_id="wf-1",
            agent_id="agent-1",
            patch_id=patch_id,
            target="facts.x",
            old_value=None,
            new_value="ok",
            reason="done",
        ),
    ]

    turns = get_agent_turns(events)

    assert len(turns) == 1
    turn = turns[0]
    assert turn.agent_id == "agent-1"
    assert turn.workflow_id == "wf-1"
    assert turn.succeeded is True
    assert turn.context_sliced is not None
    assert turn.context_sliced.agent_id == "agent-1"
    assert len(turn.prompts) == 1
    assert len(turn.model_calls) == 1
    assert turn.model_calls[0][0].call_id == call_id
    assert turn.model_calls[0][1].call_id == call_id
    assert len(turn.validation_failures) == 1
    assert turn.patch_applied is not None
    assert turn.patch_applied.patch_id == patch_id
    assert turn.total_latency_seconds == pytest.approx(1.25)
    assert turn.total_tokens == 15


def test_get_turn_for_patch_returns_matching_turn() -> None:
    patch_id = "patch-1"
    events = [
        WorkflowStarted(
            workflow_id="wf-1",
            agent_id="system",
            workflow_type="test",
            goal="test goal",
            timestamp=1.0,
        ),
        ContextSliced(
            workflow_id="wf-1",
            agent_id="agent-1",
            context_paths=["goal"],
            context_size_bytes=64,
            snapshot_workflow_id="wf-1",
        ),
        PatchApplied(
            workflow_id="wf-1",
            agent_id="agent-1",
            patch_id=patch_id,
            target="facts.x",
            old_value=None,
            new_value="ok",
            reason="done",
        ),
    ]

    turn = get_turn_for_patch(events, patch_id)

    assert turn is not None
    assert turn.patch_applied is not None
    assert turn.patch_applied.patch_id == patch_id


def test_get_turn_for_patch_returns_none_when_missing() -> None:
    events = [
        WorkflowStarted(
            workflow_id="wf-1",
            agent_id="system",
            workflow_type="test",
            goal="test goal",
            timestamp=1.0,
        ),
        ContextSliced(
            workflow_id="wf-1",
            agent_id="agent-1",
            context_paths=["goal"],
            context_size_bytes=64,
            snapshot_workflow_id="wf-1",
        ),
    ]

    assert get_turn_for_patch(events, "missing") is None
