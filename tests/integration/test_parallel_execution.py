from __future__ import annotations

import pytest

from agentstatelib import AgentGraph, SharedState, StatePatch
from agentstatelib.core.events import PatchApplied, WorkflowCompleted, WorkflowStarted


@pytest.mark.asyncio
async def test_two_agents_in_same_round() -> None:
    graph = AgentGraph()
    state = SharedState(goal="test_goal")

    @graph.node("a", context=["facts"])
    async def a(ctx: dict) -> StatePatch:
        return StatePatch(agent_id="a", target="facts.a", value="done", reason="a done")

    @graph.node("b", context=["facts"])
    async def b(ctx: dict) -> StatePatch:
        return StatePatch(agent_id="b", target="facts.b", value="done", reason="b done")

    final_state = await graph.run(state=state, start=["a", "b"])
    events = await graph._store.get_workflow(state.workflow_id)  # noqa: SLF001

    assert final_state.facts["a"] == "done"
    assert final_state.facts["b"] == "done"
    assert sum(isinstance(e, WorkflowStarted) for e in events) == 1
    assert sum(isinstance(e, PatchApplied) for e in events) == 2
    assert sum(isinstance(e, WorkflowCompleted) for e in events) == 1


@pytest.mark.asyncio
async def test_parallel_agents_read_same_snapshot() -> None:
    graph = AgentGraph()
    state = SharedState(goal="test_goal", facts={"counter": 42})

    @graph.node("a", context=["facts"])
    async def a(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="a",
            target="facts.a_seen",
            value=ctx["facts"]["counter"],
            reason="read counter",
        )

    @graph.node("b", context=["facts"])
    async def b(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="b",
            target="facts.b_seen",
            value=ctx["facts"]["counter"],
            reason="read counter",
        )

    final_state = await graph.run(state=state, start=["a", "b"])
    events = await graph._store.get_workflow(state.workflow_id)  # noqa: SLF001

    patch_events = [e for e in events if isinstance(e, PatchApplied)]
    assert len(patch_events) == 2
    assert final_state.facts["a_seen"] == 42
    assert final_state.facts["b_seen"] == 42
    assert patch_events[0].new_value == 42
    assert patch_events[1].new_value == 42


@pytest.mark.asyncio
async def test_sequential_rounds_chain() -> None:
    graph = AgentGraph()
    state = SharedState(goal="test_goal")

    @graph.node("planner", context=["goal"])
    async def planner(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="planner", target="facts.plan", value="done", reason="planned"
        )

    @graph.node("researcher", context=["facts"])
    async def researcher(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="researcher",
            target="facts.research",
            value="done",
            reason="researched",
        )

    @graph.node("writer", context=["facts"])
    async def writer(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="writer", target="facts.write", value="done", reason="written"
        )

    graph.edge(
        "planner", "researcher", lambda s: s.get("facts", {}).get("plan") == "done"
    )
    graph.edge(
        "researcher", "writer", lambda s: s.get("facts", {}).get("research") == "done"
    )

    await graph.run(state=state, start="planner")
    events = await graph._store.get_workflow(state.workflow_id)  # noqa: SLF001

    assert sum(isinstance(e, WorkflowStarted) for e in events) == 1
    assert sum(isinstance(e, WorkflowCompleted) for e in events) == 1
    assert sum(isinstance(e, PatchApplied) for e in events) == 3


@pytest.mark.asyncio
async def test_fan_out() -> None:
    graph = AgentGraph()
    state = SharedState(goal="test_goal")

    @graph.node("coordinator", context=["goal"])
    async def coordinator(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="coordinator",
            target="facts.ready",
            value=True,
            reason="coordination complete",
        )

    @graph.node("analyst_a", context=["facts"])
    async def analyst_a(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="analyst_a", target="facts.a", value="done", reason="analysis a"
        )

    @graph.node("analyst_b", context=["facts"])
    async def analyst_b(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="analyst_b", target="facts.b", value="done", reason="analysis b"
        )

    graph.edge(
        "coordinator", "analyst_a", lambda s: s.get("facts", {}).get("ready") is True
    )
    graph.edge(
        "coordinator", "analyst_b", lambda s: s.get("facts", {}).get("ready") is True
    )

    await graph.run(state=state, start="coordinator")
    events = await graph._store.get_workflow(state.workflow_id)  # noqa: SLF001

    patch_events = [e for e in events if isinstance(e, PatchApplied)]
    assert len(patch_events) == 3
    assert patch_events[1].agent_id in {"analyst_a", "analyst_b"}
    assert patch_events[2].agent_id in {"analyst_a", "analyst_b"}


@pytest.mark.asyncio
async def test_fan_out_then_fan_in() -> None:
    graph = AgentGraph()
    state = SharedState(goal="test_goal")

    @graph.node("coordinator", context=["goal"])
    async def coordinator(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="coordinator",
            target="facts.ready",
            value=True,
            reason="coordination complete",
        )

    @graph.node("analyst_a", context=["facts"])
    async def analyst_a(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="analyst_a", target="facts.a", value="done", reason="analysis a"
        )

    @graph.node("analyst_b", context=["facts"])
    async def analyst_b(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="analyst_b", target="facts.b", value="done", reason="analysis b"
        )

    @graph.node("aggregator", context=["facts"])
    async def aggregator(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="aggregator", target="facts.agg", value="done", reason="aggregated"
        )

    graph.edge(
        "coordinator", "analyst_a", lambda s: s.get("facts", {}).get("ready") is True
    )
    graph.edge(
        "coordinator", "analyst_b", lambda s: s.get("facts", {}).get("ready") is True
    )
    graph.edge(
        "analyst_a", "aggregator", lambda s: s.get("facts", {}).get("a") == "done"
    )
    graph.edge(
        "analyst_b", "aggregator", lambda s: s.get("facts", {}).get("b") == "done"
    )

    await graph.run(state=state, start="coordinator")
    events = await graph._store.get_workflow(state.workflow_id)  # noqa: SLF001

    patch_events = [e for e in events if isinstance(e, PatchApplied)]
    assert patch_events[0].agent_id == "coordinator"
    assert {patch_events[1].agent_id, patch_events[2].agent_id} == {
        "analyst_a",
        "analyst_b",
    }
    assert patch_events[3].agent_id == "aggregator"


@pytest.mark.asyncio
async def test_unknown_agent_raises() -> None:
    graph = AgentGraph()
    state = SharedState(goal="test_goal")

    with pytest.raises(ValueError):
        await graph.run(state=state, start="missing_agent")
