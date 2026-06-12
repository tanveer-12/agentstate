from __future__ import annotations

import asyncio
import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from agentstatelib.core.events import PatchApplied, WorkflowCompleted, WorkflowStarted
from agentstatelib.core.patch import StatePatch
from agentstatelib.core.state import SharedState


def test_terminal_dashboard_import_without_rich(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "rich", None)
    monkeypatch.setitem(sys.modules, "rich.live", None)
    monkeypatch.setitem(sys.modules, "rich.panel", None)
    monkeypatch.setitem(sys.modules, "rich.table", None)

    module = importlib.import_module("agentstatelib.observability.dashboard")
    assert module.WorkflowDashboard is not None


@pytest.mark.asyncio
async def test_terminal_dashboard_receives_events() -> None:
    from agentstatelib.observability.dashboard import WorkflowDashboard

    queue: asyncio.Queue = asyncio.Queue()
    dashboard = WorkflowDashboard(queue)

    e1 = MagicMock(spec=PatchApplied)
    e1.timestamp = dashboard._start_time + 1.0
    e1.agent_id = "agent-1"
    e1.target = "facts.x"

    e2 = MagicMock(spec=PatchApplied)
    e2.timestamp = dashboard._start_time + 2.0
    e2.agent_id = "agent-2"
    e2.target = "facts.y"

    await queue.put(e1)
    await queue.put(e2)
    await queue.put(None)

    with patch("agentstatelib.observability.dashboard.runtime_Live") as live_cls:
        live_instance = live_cls.return_value
        live_instance.__enter__.return_value = live_instance
        live_instance.__exit__.return_value = None
        await dashboard.run()

    assert dashboard._patch_count == 2


@pytest.mark.asyncio
async def test_graph_emits_events_to_queue_for_terminal() -> None:
    from agentstatelib.router.graph import AgentGraph

    queue: asyncio.Queue = asyncio.Queue()
    graph = AgentGraph()

    @graph.node("start")
    async def start_node(ctx) -> list[StatePatch]:
        return [
            StatePatch(
                agent_id="agent-1",
                target="facts.answer",
                value="hello",
                reason="test patch",
            )
        ]

    state = SharedState(goal="test goal", workflow_type="general")
    await graph.run(state, start="start", event_queue=queue)

    events = []
    while not queue.empty():
        item = await queue.get()
        if item is not None:
            events.append(item)

    assert any(isinstance(event, WorkflowStarted) for event in events)
    assert any(isinstance(event, PatchApplied) for event in events)
    assert any(isinstance(event, WorkflowCompleted) for event in events)
