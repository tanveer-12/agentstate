from __future__ import annotations

import asyncio

from agentstatelib import AgentGraph, SharedState, StatePatch
from agentstatelib.observability.tracing import get_tracer


def test_get_tracer_without_setup_returns_noop():
    tracer = get_tracer()
    assert hasattr(tracer, "start_as_current_span")
    with tracer.start_as_current_span("test"):
        pass


def test_noop_span_all_methods_do_nothing():
    tracer = get_tracer()
    with tracer.start_as_current_span("test") as span:
        span.set_attribute("k", "v")
        span.record_exception(ValueError("test"))


def test_graph_runs_without_tracing_configured():
    async def run_graph():
        graph = AgentGraph()

        @graph.node("planner")
        async def planner(ctx):
            return StatePatch(
                agent_id="planner",
                target="facts.plan",
                value="done",
                reason="planned",
            )

        state = SharedState(goal="test goal")
        return await graph.run(state, start="planner")

    result = asyncio.run(run_graph())
    assert result.facts["plan"] == "done"
