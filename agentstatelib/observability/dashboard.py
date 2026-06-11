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
from typing import Any

from agentstatelib.core.events import (
    AgentErrored,
    ConflictDetected,
    PatchApplied,
    WorkflowCompleted,
    WorkflowStarted,
)

runtime_Live: Any = None
runtime_Panel: Any = None
runtime_Table: Any = None

HAS_RICH = False

try:
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table

    runtime_Live = Live
    runtime_Panel = Panel
    runtime_Table = Table
    HAS_RICH = True
except ImportError:
    pass


class WorkflowDashboard:
    def __init__(self, event_queue: asyncio.Queue):
        self._event_queue = event_queue
        self._events: list = []
        self._start_time: float = time.time()
        self._current_agent: str = "starting..."
        self._conflict_count: int = 0
        self._patch_count: int = 0

    def _build_display(self) -> Any:
        table = Table(border_style="minimal")
        table.add_column("Time", width=8)
        table.add_column("Agent", width=16)
        table.add_column("Event", width=20)
        table.add_column("Target", width=30)

        for event in self._events[-15:]:
            row_style = None
            event_name = type(event).__name__
            target = ""

            if isinstance(event, PatchApplied):
                row_style = "green"
                target = getattr(event, "target", "")
            elif isinstance(event, ConflictDetected):
                row_style = "yellow"
                target = getattr(event, "path", "")
            elif isinstance(event, (WorkflowStarted, WorkflowCompleted)):
                row_style = "blue"
            elif isinstance(event, AgentErrored):
                row_style = "red"

            table.add_row(
                f"{event.timestamp - self._start_time:.1f}s",
                getattr(event, "agent_id", ""),
                event_name,
                str(target),
                style=row_style,
            )

        subtitle = (
            f"{self._patch_count} patches · {self._conflict_count} conflicts · "
            f"{time.time() - self._start_time:.1f}s elapsed"
        )
        return Panel(table, title=self._current_agent, subtitle=subtitle)

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
                    self._events.append(event)
                    if isinstance(event, PatchApplied):
                        self._patch_count += 1
                        self._current_agent = event.agent_id
                    if isinstance(event, ConflictDetected):
                        self._conflict_count += 1
                    live.update(self._build_display())
                except TimeoutError:
                    live.update(self._build_display())

    def stop(self) -> None:
        """Signal the dashboard to stop after current event is processed."""
        self._event_queue.put_nowait(None)
