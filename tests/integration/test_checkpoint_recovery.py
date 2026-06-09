import shutil

import pytest

from agentstatelib.core.events import PatchApplied, WorkflowStarted
from agentstatelib.core.patch import StatePatch
from agentstatelib.core.state import SharedState
from agentstatelib.memory.checkpoint import load_latest_checkpoint, save_checkpoint
from agentstatelib.memory.replay import ReplayDebugger, replay
from agentstatelib.memory.store import SQLiteStore


def _workflow_started(workflow_id: str) -> WorkflowStarted:
    return WorkflowStarted(
        workflow_id=workflow_id,
        agent_id="system",
        workflow_type="test",
        goal="checkpoint test",
        timestamp=1.0,
    )


def _patch_event(
    workflow_id: str,
    agent_id: str,
    target: str,
    value: object,
    timestamp: float,
    patch_id: str,
) -> PatchApplied:
    patch = StatePatch(
        agent_id=agent_id,
        target=target,
        value=value,
        reason="test",
        patch_id=patch_id,
    )
    return PatchApplied(
        workflow_id=workflow_id,
        agent_id=patch.agent_id,
        target=patch.target,
        old_value=None,
        new_value=patch.value,
        reason=patch.reason,
        patch_id=patch.patch_id,
        timestamp=timestamp,
    )


@pytest.mark.asyncio
async def test_save_and_load_checkpoint(tmp_path) -> None:
    store = SQLiteStore(str(tmp_path / "test.db"))
    workflow_id = "wf-ckpt"

    events = [
        _workflow_started(workflow_id),
        _patch_event(workflow_id, "agent_a", "facts.a", 1, 2.0, "patch-1"),
    ]
    for event in events:
        await store.append(event)

    final = replay(events)
    await save_checkpoint(final, store)
    loaded = load_latest_checkpoint(final.workflow_id)

    assert loaded is not None
    assert loaded.state.workflow_id == final.workflow_id
    assert loaded.event_count > 0

    shutil.rmtree(".checkpoints", ignore_errors=True)


@pytest.mark.asyncio
async def test_checkpoint_preserves_full_state(tmp_path) -> None:
    store = SQLiteStore(str(tmp_path / "test.db"))
    workflow_id = "wf-ckpt-2"

    events = [
        _workflow_started(workflow_id),
        _patch_event(workflow_id, "agent_a", "facts.a", 1, 2.0, "patch-1"),
        _patch_event(workflow_id, "agent_b", "facts.b", 2, 3.0, "patch-2"),
    ]
    for event in events:
        await store.append(event)

    final = replay(events)
    await save_checkpoint(final, store)
    loaded = load_latest_checkpoint(final.workflow_id)

    assert loaded is not None
    assert loaded.state.facts == final.facts
    assert set(loaded.state.artifacts.keys()) == set(final.artifacts.keys())

    shutil.rmtree(".checkpoints", ignore_errors=True)


@pytest.mark.asyncio
async def test_replay_debugger_full_walkthrough(tmp_path) -> None:
    store = SQLiteStore(str(tmp_path / "test.db"))
    workflow_id = "wf-walkthrough"

    events = [
        _workflow_started(workflow_id),
        _patch_event(workflow_id, "agent_a", "facts.a", 1, 2.0, "patch-1"),
        _patch_event(workflow_id, "agent_b", "facts.b", 2, 3.0, "patch-2"),
    ]
    for event in events:
        await store.append(event)

    final = replay(events)
    debugger = ReplayDebugger(events)

    count = 0
    last_state = None
    while True:
        try:
            _, last_state = debugger.step()
            count += 1
        except StopIteration:
            break

    assert count == len(events)
    assert last_state is not None
    assert last_state.facts.get("a") == final.facts.get("a")
    assert last_state.facts.get("b") == final.facts.get("b")

    shutil.rmtree(".checkpoints", ignore_errors=True)
