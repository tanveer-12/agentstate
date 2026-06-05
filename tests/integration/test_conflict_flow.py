from __future__ import annotations

import pytest

from agentstatelib.coordination import (
    InvariantChecker,
    InvariantViolation,
)
from agentstatelib.core.events import ConflictDetected
from agentstatelib.core.patch import StatePatch
from agentstatelib.core.state import SharedState
from agentstatelib.memory.store import InMemoryStore
from agentstatelib.router.graph import AgentGraph


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

    await graph.run(state=state, start=["agent_a", "agent_b"])

    events = await store.get_workflow(state.workflow_id)
    conflict_events = [e for e in events if isinstance(e, ConflictDetected)]
    assert len(conflict_events) >= 1


@pytest.mark.asyncio
async def test_conflict_event_has_correct_fields() -> None:
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

    await graph.run(state=state, start=["agent_a", "agent_b"])

    events = await store.get_workflow(state.workflow_id)
    conflict_events = [e for e in events if isinstance(e, ConflictDetected)]
    assert len(conflict_events) >= 1

    event = conflict_events[0]
    assert event.path == "facts.status"
    assert event.winner_agent_id in {"agent_a", "agent_b"}
    assert event.loser_agent_id in {"agent_a", "agent_b"}
    assert event.winner_agent_id != event.loser_agent_id
    assert event.resolution_strategy
    assert event.conflict_id


@pytest.mark.asyncio
async def test_conflict_final_state_is_consistent() -> None:
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

    final_state = await graph.run(state=state, start=["agent_a", "agent_b"])

    assert isinstance(final_state.facts["status"], str)
    assert final_state.facts["status"] in {"done", "failed"}


@pytest.mark.asyncio
async def test_invariant_violation_halts_workflow() -> None:
    class AlwaysError(InvariantChecker):
        def check(
            self,
            state: SharedState,
        ) -> list[InvariantViolation]:
            return [
                InvariantViolation(
                    rule_name="AlwaysError",
                    description="Always fails.",
                    severity="error",
                )
            ]

    store = InMemoryStore()

    graph = AgentGraph(
        store=store,
        invariant_checkers=[AlwaysError()],
    )

    state = SharedState(goal="test")

    @graph.node("agent_a", context=["facts"])
    async def agent_a(ctx: dict) -> StatePatch:
        return StatePatch(
            agent_id="agent_a",
            target="facts.status",
            value="done",
            reason="test",
        )

    with pytest.raises(RuntimeError):
        await graph.run(
            state,
            start="agent_a",
        )
