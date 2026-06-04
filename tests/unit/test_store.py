import pytest

from agentstatelib.core.events import PatchApplied, WorkflowStarted
from agentstatelib.memory.store import InMemoryStore, SQLiteStore, StateStore


@pytest.fixture
def in_memory_store():
    return InMemoryStore()


@pytest.fixture
def sqlite_store(tmp_path):
    return SQLiteStore(str(tmp_path / "test.db"))


@pytest.mark.parametrize("store_fixture", ["in_memory_store", "sqlite_store"])
@pytest.mark.asyncio
async def test_append_and_retrieve(request, store_fixture):
    store = request.getfixturevalue(store_fixture)
    event = WorkflowStarted(
        workflow_id="wf-1",
        agent_id="agent-1",
        workflow_type="general",
        goal="write report",
    )
    await store.append(event)
    events = await store.get_workflow(event.workflow_id)
    assert len(events) == 1
    assert events[0].event_id == event.event_id


@pytest.mark.parametrize("store_fixture", ["in_memory_store", "sqlite_store"])
@pytest.mark.asyncio
async def test_get_workflow_returns_empty_for_unknown_id(request, store_fixture):
    store = request.getfixturevalue(store_fixture)
    events = await store.get_workflow("does-not-exist")
    assert events == []


@pytest.mark.parametrize("store_fixture", ["in_memory_store", "sqlite_store"])
@pytest.mark.asyncio
async def test_count_increments_on_append(request, store_fixture):
    store = request.getfixturevalue(store_fixture)
    workflow_id = "wf-1"

    for i in range(3):
        event = WorkflowStarted(
            workflow_id=workflow_id,
            agent_id="agent-1",
            workflow_type="general",
            goal=f"goal {i}",
        )
        await store.append(event)
    assert await store.count(workflow_id) == 3


@pytest.mark.parametrize("store_fixture", ["in_memory_store", "sqlite_store"])
@pytest.mark.asyncio
async def test_since_returns_from_index(request, store_fixture):
    store = request.getfixturevalue(store_fixture)
    workflow_id = "wf-1"
    events = []

    for i in range(4):
        event = WorkflowStarted(
            workflow_id=workflow_id,
            agent_id="agent-1",
            workflow_type="general",
            goal=f"goal {i}",
        )
        events.append(event)
        await store.append(event)

    result = await store.since(workflow_id, 2)
    assert len(result) == 2
    assert result[0].event_id == events[2].event_id
    assert result[1].event_id == events[3].event_id


@pytest.mark.parametrize("store_fixture", ["in_memory_store", "sqlite_store"])
@pytest.mark.asyncio
async def test_events_preserve_type_on_retrieve(request, store_fixture):
    store = request.getfixturevalue(store_fixture)
    event = PatchApplied(
        workflow_id="wf-1",
        agent_id="agent-1",
        patch_id="patch-1",
        target="goal",
        old_value="old",
        new_value="new",
        reason="update goal",
    )
    await store.append(event)
    events = await store.get_workflow(event.workflow_id)
    assert len(events) == 1
    assert isinstance(events[0], PatchApplied)


def test_both_stores_satisfy_protocol():
    assert isinstance(InMemoryStore(), StateStore) is True
    assert isinstance(SQLiteStore(":memory:"), StateStore) is True


@pytest.mark.asyncio
async def test_get_workflow_returns_copy():
    store = InMemoryStore()

    event = WorkflowStarted(
        workflow_id="wf-1",
        agent_id="agent-1",
        workflow_type="general",
        goal="test",
    )

    await store.append(event)

    events = await store.get_workflow("wf-1")
    events.clear()

    stored = await store.get_workflow("wf-1")

    assert len(stored) == 1
