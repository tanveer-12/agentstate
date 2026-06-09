from __future__ import annotations

from agentstatelib.core.events import PatchApplied, StateEvent, WorkflowStarted
from agentstatelib.core.patch import StatePatch, apply_patch
from agentstatelib.core.state import SharedState


def replay(events: list[StateEvent]) -> SharedState:
    """
    Reconstruct SharedState from an event log by finding the WorkflowStarted event
    for metadata then applying all PatchApplied events in timestamp order.

    Pass a truncated list to reconstruct any past state.
    """
    ws_event = next((e for e in events if isinstance(e, WorkflowStarted)), None)
    if ws_event is None:
        raise ValueError("Cannot replay: no WorkflowStarted event found in event log.")
    current_state = SharedState(
        workflow_id=ws_event.workflow_id,
        workflow_type=ws_event.workflow_type,
        goal=ws_event.goal,
    )

    for event in sorted(events, key=lambda e: e.timestamp):
        if isinstance(event, PatchApplied):
            patch = StatePatch(
                agent_id=event.agent_id,
                target=event.target,
                value=event.new_value,
                reason=event.reason,
                patch_id=event.patch_id,
            )
            current_state = apply_patch(current_state, patch)

    return current_state


class ReplayDebugger:
    """
    Step through a workflow's event log to inspect state at any point.
    When a workflow produces unexpected results, use this to find the exact
    moment state diverged.

    No equivalent tool exists in LangGraph, CrewAI, or AutoGen.
    """

    def __init__(self, events: list[StateEvent]) -> None:
        self._events = sorted(events, key=lambda e: e.timestamp)
        self._cursor = 0

    def step(self) -> tuple[StateEvent, SharedState]:
        if self._cursor >= len(self._events):
            raise StopIteration("No more evnts to replay")
        self._cursor += 1
        return self._events[self._cursor - 1], replay(self._events[: self._cursor])

    def jump_to(self, index: int) -> SharedState:
        if index < 0 or index >= len(self._events):
            raise IndexError(f"Index {index} out of range [0, {len(self._events) - 1}]")
        self._cursor = index + 1
        return replay(self._events[: index + 1])

    def state_at(self, timestamp: float) -> SharedState:
        """
        Reconstruct state as it was at the given timestamp.
        Useful for finding the exact state at the moment
        a conflict or error occured.
        """
        filtered = [e for e in self._events if e.timestamp <= timestamp]
        return replay(filtered)

    def reset(self) -> None:
        self._cursor = 0

    @property
    def current_index(self) -> int:
        return self._cursor

    @property
    def total_events(self) -> int:
        return len(self._events)
