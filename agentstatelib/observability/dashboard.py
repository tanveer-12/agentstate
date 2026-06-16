"""
Live terminal dashboard for agentstatelib workflows.

Pass an asyncio.Queue as event_queue to AgentGraph.run() and the same queue
to WorkflowDashboard.  Run both concurrently with asyncio.gather.

Events are streamed one line at a time in the style of Claude Code's terminal
output: dim timestamp, coloured agent name, coloured event type, summary.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from agentstatelib.core.events import (
    AgentErrored,
    ConflictDetected,
    ContextSliced,
    ModelCalled,
    ModelReturned,
    PatchApplied,
    PromptAssembled,
    RetryAttempted,
    StateEvent,
    ValidationFailed,
    WorkflowCompleted,
    WorkflowStarted,
)

HAS_RICH = False
_console: Any = None
_Text: Any = None
_Panel: Any = None
_Rule: Any = None
_box: Any = None

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.text import Text
    import rich.box as _rich_box

    _console = Console()
    _Text    = Text
    _Panel   = Panel
    _Rule    = Rule
    _box     = _rich_box
    HAS_RICH = True
except ImportError:
    pass


# ── per-event rendering ─────────────────────────────────────────────────────

def _event_line(ev: StateEvent, start_time: float) -> tuple[str, str]:
    """Return (rich_markup_line, plain_fallback_line) for one event."""
    elapsed = f"{ev.timestamp - start_time:>6.1f}s"
    agent   = getattr(ev, "agent_id", "system") or "system"
    agent   = agent[:18]

    if isinstance(ev, WorkflowStarted):
        goal = (ev.goal or "")[:60]
        rich = f"[dim]{elapsed}[/dim]  [bold blue]workflow_started[/bold blue]  [dim]{goal}[/dim]"
        plain = f"{elapsed}  workflow_started  {goal}"

    elif isinstance(ev, WorkflowCompleted):
        rich  = f"[dim]{elapsed}[/dim]  [bold blue]workflow_completed[/bold blue]"
        plain = f"{elapsed}  workflow_completed"

    elif isinstance(ev, ContextSliced):
        paths = ", ".join(ev.context_paths[:4])
        if len(ev.context_paths) > 4:
            paths += f" +{len(ev.context_paths)-4}"
        rich  = (f"[dim]{elapsed}  {agent:<18}  context_sliced[/dim]"
                 f"  [dim]→ {paths}[/dim]")
        plain = f"{elapsed}  {agent:<18}  context_sliced  → {paths}"

    elif isinstance(ev, PromptAssembled):
        chars = len(ev.prompt_text or "")
        att   = ev.attempt_number + 1
        rich  = (f"[dim]{elapsed}  {agent:<18}  prompt_assembled"
                 f"  {chars} chars  attempt {att}[/dim]")
        plain = f"{elapsed}  {agent:<18}  prompt_assembled  {chars} chars  attempt {att}"

    elif isinstance(ev, ModelCalled):
        model = ev.model or "model"
        rich  = (f"[dim]{elapsed}[/dim]  [cyan]{agent:<18}[/cyan]"
                 f"  [yellow]model_called[/yellow]"
                 f"  [dim]→ {model}…[/dim]")
        plain = f"{elapsed}  {agent:<18}  model_called  → {model}…"

    elif isinstance(ev, ModelReturned):
        lat = f"{ev.latency_seconds:.2f}s" if ev.latency_seconds is not None else "?s"
        tok = (ev.input_tokens or 0) + (ev.output_tokens or 0)
        cost = f"  ${ev.estimated_cost_usd:.4f}" if ev.estimated_cost_usd else ""
        rich  = (f"[dim]{elapsed}[/dim]  [cyan]{agent:<18}[/cyan]"
                 f"  [green]model_returned[/green]"
                 f"  [green]✓ {lat} · {tok} tokens{cost}[/green]")
        plain = f"{elapsed}  {agent:<18}  model_returned  ✓ {lat} · {tok} tokens{cost}"

    elif isinstance(ev, PatchApplied):
        rich  = (f"[dim]{elapsed}[/dim]  [cyan]{agent:<18}[/cyan]"
                 f"  [bold green]patch_applied[/bold green]"
                 f"  [bold green]→ {ev.target}[/bold green]"
                 f"  [dim]{ev.reason or ''}[/dim]")
        plain = f"{elapsed}  {agent:<18}  patch_applied  → {ev.target}  {ev.reason or ''}"

    elif isinstance(ev, ValidationFailed):
        att  = ev.attempt_number + 1
        rich  = (f"[dim]{elapsed}[/dim]  [cyan]{agent:<18}[/cyan]"
                 f"  [red]validation_failed[/red]"
                 f"  [red]{ev.error_type}  attempt {att}[/red]")
        plain = f"{elapsed}  {agent:<18}  validation_failed  {ev.error_type}  attempt {att}"

    elif isinstance(ev, RetryAttempted):
        rich  = (f"[dim]{elapsed}[/dim]  [cyan]{agent:<18}[/cyan]"
                 f"  [yellow]retry_attempted[/yellow]"
                 f"  [dim]attempt {ev.attempt_number}[/dim]")
        plain = f"{elapsed}  {agent:<18}  retry_attempted  attempt {ev.attempt_number}"

    elif isinstance(ev, ConflictDetected):
        rich  = (f"[dim]{elapsed}[/dim]"
                 f"  [yellow]conflict_detected[/yellow]"
                 f"  [yellow]{ev.path}  → {ev.winner_agent_id} wins[/yellow]")
        plain = f"{elapsed}  conflict_detected  {ev.path}  → {ev.winner_agent_id} wins"

    elif isinstance(ev, AgentErrored):
        msg = (ev.error_message or "")[:60]
        rich  = (f"[dim]{elapsed}[/dim]  [cyan]{agent:<18}[/cyan]"
                 f"  [bold red]agent_errored[/bold red]"
                 f"  [red]{ev.error_type}: {msg}[/red]")
        plain = f"{elapsed}  {agent:<18}  agent_errored  {ev.error_type}: {msg}"

    else:
        name  = type(ev).__name__
        rich  = f"[dim]{elapsed}  {agent:<18}  {name}[/dim]"
        plain = f"{elapsed}  {agent:<18}  {name}"

    return rich, plain


# ── WorkflowDashboard ───────────────────────────────────────────────────────

class WorkflowDashboard:
    """
    Streams workflow events to the terminal as they arrive.

    Usage::

        queue: asyncio.Queue = asyncio.Queue()
        dashboard = WorkflowDashboard(queue)
        state, _ = await asyncio.gather(
            run_workflow(..., event_queue=queue),
            dashboard.run(),
        )
    """

    def __init__(self, event_queue: asyncio.Queue[StateEvent | None]) -> None:
        self._queue      = event_queue
        self._start_time: float = time.time()
        self._patch_count    = 0
        self._conflict_count = 0
        self._retry_count    = 0
        self._total_tokens   = 0
        self._total_cost     = 0.0
        self._goal           = ""
        self._workflow_type  = ""
        self._events: list[StateEvent] = []

    def _print(self, rich_line: str, plain_line: str) -> None:
        if HAS_RICH:
            _console.print(rich_line)
        else:
            print(plain_line)

    def _handle(self, ev: StateEvent) -> None:
        self._events.append(ev)

        if isinstance(ev, WorkflowStarted):
            self._start_time    = ev.timestamp
            self._goal          = ev.goal or ""
            self._workflow_type = ev.workflow_type or ""

        if isinstance(ev, ModelReturned):
            self._total_tokens += (ev.input_tokens or 0) + (ev.output_tokens or 0)
            self._total_cost   += ev.estimated_cost_usd or 0.0

        if isinstance(ev, PatchApplied):
            self._patch_count += 1

        if isinstance(ev, ConflictDetected):
            self._conflict_count += 1

        if isinstance(ev, (ValidationFailed, RetryAttempted)):
            self._retry_count += 1

    def _print_header(self) -> None:
        goal_short = self._goal[:60] if self._goal else "workflow"
        wf_type    = self._workflow_type or ""
        if HAS_RICH:
            title = f"[bold]{wf_type}[/bold]" if wf_type else "agentstatelib"
            _console.print(
                _Panel(
                    f"[dim]goal:[/dim] {goal_short}",
                    title=title,
                    expand=False,
                    border_style="blue",
                )
            )
            _console.print()
            # Column header
            _console.print(
                f"[dim]{'elapsed':>7}  {'agent':<18}  {'event':<20}  summary[/dim]"
            )
            _console.rule(style="dim")
        else:
            print(f"\n=== {wf_type or 'agentstatelib'} — {goal_short} ===")
            print(f"{'elapsed':>7}  {'agent':<18}  {'event':<20}  summary")
            print("-" * 80)

    def _print_summary(self) -> None:
        elapsed = time.time() - self._start_time
        parts = [
            f"{len(self._events)} events",
            f"{self._patch_count} patches",
            f"{self._conflict_count} conflicts",
            f"{self._retry_count} retries",
            f"{self._total_tokens} tokens",
            f"{elapsed:.1f}s",
        ]
        if self._total_cost > 0:
            parts.append(f"${self._total_cost:.4f}")
        summary = " · ".join(parts)

        if HAS_RICH:
            _console.print()
            _console.rule(style="dim")
            _console.print(f"[dim]{summary}[/dim]")
            _console.print()
        else:
            print("\n" + "-" * 80)
            print(summary)
            print()

    async def run(self) -> None:
        """Consume events from the queue and stream them to the terminal."""
        if not HAS_RICH:
            import warnings
            warnings.warn(
                "rich is not installed — falling back to plain text output. "
                "Install with: pip install agentstate-lib[dashboard]",
                stacklevel=2,
            )

        header_printed = False

        while True:
            try:
                ev = await asyncio.wait_for(self._queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                continue

            if ev is None:
                break

            # Print header once, before the first real event
            if not header_printed:
                if isinstance(ev, WorkflowStarted):
                    self._start_time = ev.timestamp
                    self._goal = ev.goal or ""
                    self._workflow_type = ev.workflow_type or ""
                self._print_header()
                header_printed = True

            self._handle(ev)
            rich_line, plain_line = _event_line(ev, self._start_time)
            self._print(rich_line, plain_line)

        self._print_summary()

    def stop(self) -> None:
        """Signal the dashboard to stop after the current event is processed."""
        self._queue.put_nowait(None)
