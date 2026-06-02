from __future__ import annotations

import asyncio

import pytest

from agentstatelib import AgentGraph, SharedState, StatePatch
from agentstatelib.core.events import ConflictDetected
from agentstatelib.memory.store import InMemoryStore
from agentstatelib.coordination import InvariantChecker, InvariantViolation


@pytest.mark.asyncio
async def test_conflict_detected_and_logged_in_store() -> None:
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    state = SharedState(goal="test_goal")

    @graph.node("agent_a", context=["facts"])
    async def agent_a(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="agent_a",
            target="facts.status",
            value="done",
            reason="agent_a sets done",
        )

    @graph.node("agent_b", context=["facts"])
    async def agent_b(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="agent_b",
            target="facts.status",
            value="failed",
            reason="agent_b sets failed",
        )

    # Simple linear edge: a -> b
    graph.edge("agent_a", "agent_b")

    final_state = await graph.run(state=state, start="agent_a")

    events = await store.get_workflow(state.workflow_id)
    conflict_events = [e for e in events if isinstance(e, ConflictDetected)]
    assert len(conflict_events) >= 1


@pytest.mark.asyncio
async def test_invariant_violation_halts_workflow() -> None:
    store = InMemoryStore()
    graph = AgentGraph(store=store)

    state = SharedState(goal="test_goal")

    @graph.node("agent_a", context=["facts"])
    async def agent_a(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="agent_a",
            target="facts.status",
            value="done",
            reason="irrelevant",
        )

    class AlwaysErrorInvariant:
        def check(self, state: SharedState) -> list[InvariantViolation]:
            return [
                InvariantViolation(
                    rule_name="AlwaysErrorInvariant",
                    description="Always fails.",
                    severity="error",
                )
            ]

    graph.add_invariant(AlwaysErrorInvariant())

    with pytest.raises(RuntimeError):
        await graph.run(state=state, start="agent_a")