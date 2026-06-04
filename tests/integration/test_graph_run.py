from __future__ import annotations

import asyncio

import pytest

from agentstatelib.core.patch import StatePatch
from agentstatelib.core.state import SharedState
from agentstatelib.router.graph import AgentGraph


@pytest.mark.asyncio
async def test_single_agent_workflow() -> None:
    graph = AgentGraph()

    @graph.node("agent_a")
    async def stub_agent(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="a",
            target="facts.done",
            value=True,
            reason="test",
        )

    final = await graph.run(
        SharedState(goal="test"),
        start="agent_a",
    )

    assert final.facts.get("done") is True


@pytest.mark.asyncio
async def test_two_agent_sequential_pipeline() -> None:
    graph = AgentGraph()

    @graph.node("agent_a")
    async def agent_a(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="a",
            target="facts.step",
            value=1,
            reason="step one",
        )

    @graph.node("agent_b")
    async def agent_b(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="b",
            target="facts.step",
            value=2,
            reason="step two",
        )

    graph.edge(
        "agent_a",
        "agent_b",
        condition=lambda s: s.get("facts", {}).get("step") == 1,
    )

    final = await graph.run(
        SharedState(goal="test"),
        start="agent_a",
    )

    assert final.facts.get("step") == 2


@pytest.mark.asyncio
async def test_unknown_start_agent_raises() -> None:
    graph = AgentGraph()

    with pytest.raises(ValueError):
        await graph.run(
            SharedState(goal="x"),
            start="nonexistent",
        )
