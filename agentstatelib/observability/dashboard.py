"""
Live terminal dashboard for agentstatelib workflows. Install with
pip install agentstate-lib[dashboard].
Pass an asyncio.Queue as event_queue to AgentGraph.run()
and the same queue to WorkflowDashboard.
Run both concurrently with asyncio.gather.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from rich import box

from agentstatelib.core.events import (
    AgentErrored,
    ConflictDetected,
    ContextSliced,
    ModelCalled,
    ModelReturned,
    PatchApplied,
    PromptAssembled,
    StateEvent,
    ValidationFailed,
    WorkflowCompleted,
    WorkflowStarted,
)

runtime_Live: Any = None
runtime_Panel: Any = None
runtime_Table: Any = None
runtime_Group: Any = None
runtime_Text: Any = None


HAS_RICH = False


try:
    from rich.console import Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    runtime_Live = Live
    runtime_Panel = Panel
    runtime_Table = Table
    runtime_Group = Group
    runtime_Text = Text
    HAS_RICH = True
except ImportError:
    pass


@dataclass
class _FailureView:
    message: str
    error_type: str
    attempt_number: int


@dataclass
class _TurnView:
    agent_id: str
    workflow_id: str
    turn_number: int
    started_at: float
    attempt_count: int = 0
    succeeded: bool = False
    context_paths: list[str] = field(default_factory=list)
    prompt_text: str = ""
    model_name: str = ""
    model_latency_seconds: float | None = None
    validation_failures: list[_FailureView] = field(default_factory=list)
    patch_target: str = ""
    patch_reason: str = ""
    patch_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    ended_at: float | None = None
    in_progress: bool = True

    @property
    def duration_seconds(self) -> float:
        end = self.ended_at if self.ended_at is not None else time.time()
        return max(0.0, end - self.started_at)


class WorkflowDashboard:
    def __init__(self, event_queue: asyncio.Queue[StateEvent | None]):
        self._event_queue = event_queue
        self._events: list[StateEvent] = []
        self._start_time: float = time.time()
        self._workflow_goal: str = ""
        self._workflow_status: str = "starting"
        self._current_agent: str = "starting..."
        self._conflict_count: int = 0
        self._patch_count: int = 0
        self._retry_count: int = 0
        self._total_tokens: int = 0
        self._estimated_cost_usd: float = 0.0
        self._turns: list[_TurnView] = []
        self._current_turn: _TurnView | None = None
        self._expanded_turn: int | None = None
        self._model_call_started_at: float | None = None
        self._active_model_name: str = ""

    def _build_display(self) -> Any:
        header = self._build_header()
        turns = self._build_turns_panel()
        summary = self._build_summary()

        return runtime_Group(header, turns, summary)

    def _build_header(self) -> Any:
        goal = self._workflow_goal or "workflow"
        goal = goal if len(goal) <= 40 else goal[:37] + "..."
        elapsed = time.time() - self._start_time
        status = f"[green]{self._workflow_status}[/green]"
        agent = self._current_agent or "starting..."
        parts = [
            f"goal: {goal}",
            f"status: {status}",
            f"elapsed: {elapsed:.1f}s",
            f"agent: {agent}",
            f"retries: {self._retry_count}",
            f"conflicts: {self._conflict_count}",
        ]
        if self._total_tokens > 0 or self._estimated_cost_usd > 0:
            parts.append(f"tokens: {self._total_tokens}")
            parts.append(f"cost: ${self._estimated_cost_usd:.2f}")
        return runtime_Panel(" · ".join(parts), title="Overview", box=box.MINIMAL)

    def _build_turns_panel(self) -> Any:
        table = runtime_Table(box=box.MINIMAL, show_header=True, expand=True)
        table.add_column("Turn", width=6)
        table.add_column("Agent", width=16)
        table.add_column("Attempts", width=8)
        table.add_column("Duration", width=10)
        table.add_column("Result", width=10)
        table.add_column("Details")

        for idx, turn in enumerate(self._turns, start=1):
            badge = "[yellow]●[/yellow]"
            if turn.succeeded:
                badge = "[green]✓[/green]"
            elif turn.in_progress:
                badge = "[yellow]◌[/yellow]"
            else:
                badge = "[red]✗[/red]"

            details = (
                self._render_turn_details(turn)
                if self._expanded_turn == idx - 1
                else ""
            )
            if (
                self._expanded_turn is None
                and idx == len(self._turns)
                and not turn.in_progress
            ):
                details = self._render_turn_details(turn)

            table.add_row(
                str(idx),
                turn.agent_id,
                str(turn.attempt_count),
                f"{turn.duration_seconds:.1f}s",
                badge,
                details,
            )

        return runtime_Panel(table, title="Agent Turns", box=box.MINIMAL)

    def _render_turn_details(self, turn: _TurnView) -> str:
        lines: list[str] = []
        if turn.context_paths:
            lines.append(f"context: {', '.join(turn.context_paths)}")
        if turn.prompt_text:
            prompt = turn.prompt_text
            if len(prompt) > 200:
                prompt = prompt[:200] + "..."
            lines.append(f"prompt: {prompt}")
        if turn.model_name:
            latency = (
                f"{turn.model_latency_seconds:.2f}s"
                if turn.model_latency_seconds is not None
                else "pending"
            )
            lines.append(f"model: {turn.model_name} · latency: {latency}")
        for failure in turn.validation_failures:
            lines.append(
                f"[red]validation: {failure.error_type} - {failure.message}[/red]"
            )
        if turn.patch_target:
            lines.append(f"patch: {turn.patch_target} — {turn.patch_reason}")
        return "\n".join(lines)

    def _build_summary(self) -> Any:
        elapsed = time.time() - self._start_time
        text = (
            f"{self._patch_count} patches · {self._conflict_count} conflicts · "
            f"{self._retry_count} retries · {self._total_tokens} tokens · "
            f"{elapsed:.1f}s"
        )
        return runtime_Panel(text, title="Summary", box=box.MINIMAL)

    def _ensure_current_turn(self, event: StateEvent) -> _TurnView:
        if self._current_turn is None:
            self._current_turn = _TurnView(
                agent_id=getattr(event, "agent_id", "unknown"),
                workflow_id=event.workflow_id,
                turn_number=len(self._turns) + 1,
                started_at=event.timestamp,
            )
            self._turns.append(self._current_turn)
        return self._current_turn

    def _handle_event(self, event: StateEvent) -> None:
        self._events.append(event)

        if isinstance(event, WorkflowStarted):
            self._start_time = event.timestamp
            self._workflow_goal = event.goal
            self._workflow_status = "running"
            self._current_agent = event.agent_id
            return

        if isinstance(event, WorkflowCompleted):
            self._workflow_status = "completed"
            return

        if isinstance(event, ConflictDetected):
            self._conflict_count += 1
            return

        if isinstance(event, ContextSliced):
            self._current_turn = _TurnView(
                agent_id=event.agent_id,
                workflow_id=event.workflow_id,
                turn_number=len(self._turns) + 1,
                started_at=event.timestamp,
                context_paths=list(event.context_paths),
            )
            self._turns.append(self._current_turn)
            self._current_agent = event.agent_id
            self._model_call_started_at = None
            self._active_model_name = ""
            return

        if self._current_turn is None:
            self._current_turn = self._ensure_current_turn(event)

        if isinstance(event, PromptAssembled):
            self._current_turn.prompt_text = event.prompt_text
            self._current_turn.attempt_count = max(
                self._current_turn.attempt_count, event.attempt_number + 1
            )
            return

        if isinstance(event, ModelCalled):
            self._current_turn.model_name = event.model
            self._current_turn.attempt_count = max(
                self._current_turn.attempt_count, event.attempt_number + 1
            )
            self._model_call_started_at = event.timestamp
            self._active_model_name = event.model
            return

        if isinstance(event, ModelReturned):
            if self._model_call_started_at is not None:
                self._current_turn.model_latency_seconds = (
                    event.timestamp - self._model_call_started_at
                )
            self._total_tokens += (event.input_tokens or 0) + (event.output_tokens or 0)
            self._estimated_cost_usd += event.estimated_cost_usd or 0.0
            return

        if isinstance(event, ValidationFailed):
            self._retry_count += 1
            self._current_turn.validation_failures.append(
                _FailureView(
                    message=event.error_message,
                    error_type=event.error_type,
                    attempt_number=event.attempt_number,
                )
            )
            return

        if isinstance(event, PatchApplied):
            self._patch_count += 1
            self._current_turn.succeeded = True
            self._current_turn.in_progress = False
            self._current_turn.ended_at = event.timestamp
            self._current_turn.patch_target = event.target
            self._current_turn.patch_reason = event.reason
            self._current_turn.patch_id = event.patch_id
            self._current_agent = event.agent_id
            self._current_turn = None
            self._model_call_started_at = None
            self._active_model_name = ""
            return

        if isinstance(event, AgentErrored):
            self._current_turn.succeeded = False
            self._current_turn.in_progress = False
            self._current_turn.ended_at = event.timestamp
            self._current_turn = None
            self._model_call_started_at = None
            self._active_model_name = ""

    async def run(self) -> None:
        if not HAS_RICH:
            raise ImportError(
                "rich required. Install with: pip install agentstate-lib[dashboard]"
            )

        live = runtime_Live(refresh_per_second=4)
        with live:
            while True:
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(), timeout=0.25
                    )
                    if event is None:
                        break
                    self._handle_event(event)
                    live.update(self._build_display())
                except TimeoutError:
                    live.update(self._build_display())

    def stop(self) -> None:
        """Signal the dashboard to stop after current event is processed."""
        self._event_queue.put_nowait(None)
