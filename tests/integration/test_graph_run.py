from __future__ import annotations

import pytest

from agentstatelib.core.patch import StatePatch
from agentstatelib.core.state import SharedState
from agentstatelib.router.graph import AgentGraph


@pytest.mark.asyncio
async def test_single_agent_workflow() -> None:
    graph = AgentGraph()

    @graph.node("agent_a")
    async def stub_agent(context: dict) -> StatePatch:
        return StatePatch(
            agent_id="agent_a",
            target="facts.done",
            value=True,
            reason="test",
        )

    state = SharedState(goal="test")

    final_state = await graph.run(state, start="agent_a")

    assert final_state.facts.get("done") is True


@pytest.mark.asyncio
async def test_two_agent_pipeline_in_order() -> None:
    graph = AgentGraph()

    @graph.node("first")
    async def first_agent(context: dict) -> StatePatch:
        return StatePatch(
            agent_id="first",
            target="facts.step",
            value=1,
            reason="set step to 1",
        )

    @graph.node("second")
    async def second_agent(context: dict) -> StatePatch:
        return StatePatch(
            agent_id="second",
            target="facts.step",
            value=2,
            reason="set step to 2",
        )

    graph.edge(
        "first",
        "second",
        condition=lambda s: s.get("facts", {}).get("step") == 1,
    )

    state = SharedState(goal="test")

    final_state = await graph.run(state, start="first")

    assert final_state.facts["step"] == 2


@pytest.mark.asyncio
async def test_graph_raises_on_unknown_start_agent() -> None:
    graph = AgentGraph()
    state = SharedState(goal="x")

    with pytest.raises(ValueError):
        await graph.run(state, start="nonexistent")