from __future__ import annotations

import pytest

from agentstatelib.core.events import PatchApplied
from agentstatelib.core.patch import StatePatch, apply_patch
from agentstatelib.core.state import SharedState
from agentstatelib.memory.store import InMemoryStore
from agentstatelib.router.graph import AgentGraph


@pytest.mark.asyncio
async def test_two_agents_in_same_round() -> None:
    store = InMemoryStore()
    graph = AgentGraph(store=store)
    state = SharedState(goal="test")

    @graph.node("agent_a", context=["facts"])
    async def agent_a(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="agent_a",
            target="facts.result_a",
            value=1,
            reason="result a",
        )

    @graph.node("agent_b", context=["facts"])
    async def agent_b(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="agent_b",
            target="facts.result_b",
            value=2,
            reason="result b",
        )

    final = await graph.run(state, start=["agent_a", "agent_b"])

    events = await store.get_workflow(state.workflow_id)
    patch_events = [e for e in events if isinstance(e, PatchApplied)]

    assert len(patch_events) == 2
    assert "result_a" in final.facts
    assert "result_b" in final.facts


@pytest.mark.asyncio
async def test_parallel_agents_read_same_snapshot() -> None:
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    state = SharedState(goal="test")

    setup_patch = StatePatch(
        agent_id="setup",
        target="facts.counter",
        value=42,
        reason="seed counter",
    )
    state = apply_patch(state, setup_patch)

    @graph.node("agent_a", context=["facts.counter"])
    async def agent_a(ctx: dict) -> StatePatch:
        counter = ctx.get("facts", {}).get("counter")
        return StatePatch(
            agent_id="agent_a",
            target="facts.a_saw",
            value=counter,
            reason="read counter",
        )

    @graph.node("agent_b", context=["facts.counter"])
    async def agent_b(ctx: dict) -> StatePatch:
        counter = ctx.get("facts", {}).get("counter")
        return StatePatch(
            agent_id="agent_b",
            target="facts.b_saw",
            value=counter,
            reason="read counter",
        )

    final = await graph.run(state, start=["agent_a", "agent_b"])

    events = await store.get_workflow(state.workflow_id)
    patch_events = [e for e in events if isinstance(e, PatchApplied)]

    assert len(patch_events) == 2
    assert final.facts["a_saw"] == 42
    assert final.facts["b_saw"] == 42

    values = {e.new_value for e in patch_events}
    assert values == {42}


@pytest.mark.asyncio
async def test_sequential_rounds_chain() -> None:
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    state = SharedState(goal="test")

    @graph.node("planner", context=["goal"])
    async def planner(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="planner",
            target="facts.plan",
            value="done",
            reason="planned",
        )

    @graph.node("researcher", context=["facts"])
    async def researcher(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="researcher",
            target="facts.sources",
            value=["s1"],
            reason="research complete",
        )

    @graph.node("writer", context=["facts"])
    async def writer(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="writer",
            target="facts.draft",
            value="draft",
            reason="draft written",
        )

    graph.edge("planner", "researcher", lambda s: "plan" in s.get("facts", {}))
    graph.edge("researcher", "writer", lambda s: "sources" in s.get("facts", {}))

    await graph.run(state, start="planner")

    events = await store.get_workflow(state.workflow_id)
    patch_events = [e for e in events if isinstance(e, PatchApplied)]

    targets = [e.target for e in patch_events]

    assert targets == [
        "facts.plan",
        "facts.sources",
        "facts.draft",
    ]


@pytest.mark.asyncio
async def test_fan_out() -> None:
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    state = SharedState(goal="test")

    @graph.node("coordinator")
    async def coordinator(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="coordinator",
            target="facts.started",
            value=True,
            reason="start",
        )

    @graph.node("analyst_a")
    async def analyst_a(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="analyst_a",
            target="facts.result_a",
            value=1,
            reason="analysis a",
        )

    @graph.node("analyst_b")
    async def analyst_b(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="analyst_b",
            target="facts.result_b",
            value=2,
            reason="analysis b",
        )

    graph.edge("coordinator", "analyst_a")
    graph.edge("coordinator", "analyst_b")

    final = await graph.run(state, start="coordinator")

    events = await store.get_workflow(state.workflow_id)
    patch_events = [e for e in events if isinstance(e, PatchApplied)]

    assert patch_events[0].target == "facts.started"

    targets = {e.target for e in patch_events}

    assert "facts.result_a" in targets
    assert "facts.result_b" in targets

    assert final.facts["started"] is True
    assert final.facts["result_a"] == 1
    assert final.facts["result_b"] == 2


@pytest.mark.asyncio
async def test_fan_out_then_fan_in() -> None:
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    state = SharedState(goal="test")

    @graph.node("coordinator")
    async def coordinator(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="coordinator",
            target="facts.started",
            value=True,
            reason="start",
        )

    @graph.node("analyst_a")
    async def analyst_a(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="analyst_a",
            target="facts.result_a",
            value=1,
            reason="analysis a",
        )

    @graph.node("analyst_b")
    async def analyst_b(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="analyst_b",
            target="facts.result_b",
            value=2,
            reason="analysis b",
        )

    @graph.node("aggregator")
    async def aggregator(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="aggregator",
            target="facts.summary",
            value="complete",
            reason="aggregate",
        )

    graph.edge("coordinator", "analyst_a")
    graph.edge("coordinator", "analyst_b")
    graph.edge("analyst_a", "aggregator")
    graph.edge("analyst_b", "aggregator")

    await graph.run(state, start="coordinator")

    events = await store.get_workflow(state.workflow_id)
    patch_events = [e for e in events if isinstance(e, PatchApplied)]

    assert patch_events[0].target == "facts.started"

    analyst_targets = {
        patch_events[1].target,
        patch_events[2].target,
    }

    assert analyst_targets == {
        "facts.result_a",
        "facts.result_b",
    }

    assert patch_events[-1].target == "facts.summary"

    aggregator_events = [e for e in patch_events if e.target == "facts.summary"]

    assert len(aggregator_events) == 1


@pytest.mark.asyncio
async def test_parallel_start_with_list() -> None:
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    state = SharedState(goal="test")

    @graph.node("agent_a")
    async def agent_a(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="agent_a",
            target="facts.a",
            value=1,
            reason="a",
        )

    @graph.node("agent_b")
    async def agent_b(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="agent_b",
            target="facts.b",
            value=2,
            reason="b",
        )

    await graph.run(state, start=["agent_a", "agent_b"])

    events = await store.get_workflow(state.workflow_id)
    patch_events = [e for e in events if isinstance(e, PatchApplied)]

    assert len(patch_events) == 2


@pytest.mark.asyncio
async def test_unknown_start_agent_raises() -> None:
    graph = AgentGraph()
    state = SharedState(goal="test")

    with pytest.raises(ValueError):
        await graph.run(state, start="not_registered")
