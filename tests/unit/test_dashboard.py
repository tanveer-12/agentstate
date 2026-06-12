from __future__ import annotations

import asyncio
import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from agentstatelib.core.events import (
    ConflictDetected,
    ContextSliced,
    ModelCalled,
    ModelReturned,
    PatchApplied,
    PromptAssembled,
    ValidationFailed,
    WorkflowCompleted,
    WorkflowStarted,
)
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

    await queue.put(
        WorkflowStarted(
            workflow_id="wf-1",
            agent_id="system",
            workflow_type="general",
            goal="test goal",
            timestamp=dashboard._start_time + 0.1,
        )
    )
    await queue.put(
        ContextSliced(
            workflow_id="wf-1",
            agent_id="agent-1",
            context_paths=["goal", "facts"],
            context_size_bytes=128,
            snapshot_workflow_id="wf-1",
        )
    )
    await queue.put(
        PromptAssembled(
            workflow_id="wf-1",
            agent_id="agent-1",
            prompt_text="You are a helpful agent. Return JSON only.",
            system_prompt_length=24,
            context_length=128,
            is_correction_attempt=False,
            attempt_number=0,
        )
    )
    call_id = "call-1"
    await queue.put(
        ModelCalled(
            workflow_id="wf-1",
            agent_id="agent-1",
            model="llama3:8b",
            provider="ollama",
            attempt_number=0,
            call_id=call_id,
        )
    )
    await queue.put(
        ModelReturned(
            workflow_id="wf-1",
            agent_id="agent-1",
            call_id=call_id,
            raw_response='{"target":"facts.x","value":"hello","reason":"test"}',
            latency_seconds=0.25,
            input_tokens=12,
            output_tokens=8,
            estimated_cost_usd=0.02,
        )
    )
    await queue.put(
        ValidationFailed(
            workflow_id="wf-1",
            agent_id="agent-1",
            attempt_number=0,
            error_type="json_decode_error",
            error_message="bad json",
            raw_output="not json",
            will_retry=True,
        )
    )
    await queue.put(
        PatchApplied(
            workflow_id="wf-1",
            agent_id="agent-1",
            patch_id="patch-1",
            target="facts.x",
            old_value=None,
            new_value="hello",
            reason="test patch",
            timestamp=dashboard._start_time + 1.0,
        )
    )
    await queue.put(
        ConflictDetected(
            workflow_id="wf-1",
            agent_id="system",
            conflict_id="c-1",
            path="facts.x",
            winner_agent_id="agent-1",
            loser_agent_id="agent-2",
            resolution_strategy="last_write_wins",
            existing_patch=None,
            incoming_patch=None,
        )
    )
    await queue.put(
        WorkflowCompleted(
            workflow_id="wf-1",
            agent_id="system",
            final_status="complete",
            timestamp=dashboard._start_time + 1.5,
        )
    )
    await queue.put(None)

    with patch("agentstatelib.observability.dashboard.runtime_Live") as live_cls:
        live_instance = live_cls.return_value
        live_instance.__enter__.return_value = live_instance
        live_instance.__exit__.return_value = None
        await dashboard.run()

    assert dashboard._patch_count == 1
    assert dashboard._conflict_count == 1
    assert dashboard._retry_count == 1
    assert dashboard._total_tokens == 20
    assert dashboard._estimated_cost_usd == pytest.approx(0.02)
    assert dashboard._workflow_goal == "test goal"
    assert len(dashboard._turns) == 1


@pytest.mark.asyncio
async def test_dashboard_render_includes_trace_details() -> None:
    from agentstatelib.observability.dashboard import WorkflowDashboard

    queue: asyncio.Queue = asyncio.Queue()
    dashboard = WorkflowDashboard(queue)

    await queue.put(
        WorkflowStarted(
            workflow_id="wf-1",
            agent_id="system",
            workflow_type="general",
            goal="test goal for dashboard rendering",
            timestamp=dashboard._start_time,
        )
    )
    await queue.put(
        ContextSliced(
            workflow_id="wf-1",
            agent_id="agent-1",
            context_paths=["goal", "facts"],
            context_size_bytes=128,
            snapshot_workflow_id="wf-1",
        )
    )
    await queue.put(
        PromptAssembled(
            workflow_id="wf-1",
            agent_id="agent-1",
            prompt_text="You are a helpful agent. Return valid JSON with target/value/reason.",
            system_prompt_length=24,
            context_length=128,
            is_correction_attempt=False,
            attempt_number=0,
        )
    )
    call_id = "call-1"
    await queue.put(
        ModelCalled(
            workflow_id="wf-1",
            agent_id="agent-1",
            model="llama3:8b",
            provider="ollama",
            attempt_number=0,
            call_id=call_id,
        )
    )
    await queue.put(
        ModelReturned(
            workflow_id="wf-1",
            agent_id="agent-1",
            call_id=call_id,
            raw_response='{"target":"facts.x","value":"hello","reason":"test"}',
            latency_seconds=0.25,
            input_tokens=12,
            output_tokens=8,
            estimated_cost_usd=0.02,
        )
    )
    await queue.put(
        PatchApplied(
            workflow_id="wf-1",
            agent_id="agent-1",
            patch_id="patch-1",
            target="facts.x",
            old_value=None,
            new_value="hello",
            reason="test patch",
            timestamp=dashboard._start_time + 1.0,
        )
    )
    await queue.put(None)

    with patch("agentstatelib.observability.dashboard.runtime_Live") as live_cls:
        live_instance = live_cls.return_value
        live_instance.__enter__.return_value = live_instance
        live_instance.__exit__.return_value = None
        await dashboard.run()

    display = dashboard._build_display()
    rendered = str(display)

    assert "test goal for dashboard rendering" in rendered
    assert "agent-1" in rendered
    assert "facts.x" in rendered
    assert "helpful agent" in rendered
    assert "patches" in rendered
    assert "conflicts" in rendered
    assert "retries" in rendered
    assert "tokens" in rendered


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
    assert any(isinstance(event, ContextSliced) for event in events)
    assert any(isinstance(event, PatchApplied) for event in events)
    assert any(isinstance(event, WorkflowCompleted) for event in events)
