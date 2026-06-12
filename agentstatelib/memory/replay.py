from __future__ import annotations

from dataclasses import dataclass, field

from agentstatelib.core.events import (
    AgentErrored,
    ContextSliced,
    ModelCalled,
    ModelReturned,
    PatchApplied,
    PromptAssembled,
    RetryAttempted,
    StateEvent,
    ToolCalled,
    ToolReturned,
    ValidationFailed,
    WorkflowStarted,
)
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


@dataclass
class AgentTurn:
    agent_id: str
    workflow_id: str
    attempt_count: int
    succeeded: bool
    context_sliced: ContextSliced | None
    prompts: list[PromptAssembled] = field(default_factory=list)
    model_calls: list[tuple[ModelCalled, ModelReturned]] = field(default_factory=list)
    validation_failures: list[ValidationFailed] = field(default_factory=list)
    patch_applied: PatchApplied | None = None
    tool_calls: list[tuple[ToolCalled, ToolReturned | None]] = field(
        default_factory=list
    )
    total_latency_seconds: float = 0.0
    total_tokens: int = 0


def get_model_call_pairs(
    events: list[StateEvent],
) -> list[tuple[ModelCalled, ModelReturned]]:
    calls: dict[str, ModelCalled] = {}
    pairs: list[tuple[ModelCalled, ModelReturned]] = []

    for event in events:
        if isinstance(event, ModelCalled):
            calls[event.call_id] = event
        elif isinstance(event, ModelReturned) and event.call_id in calls:
            pairs.append((calls[event.call_id], event))

    return pairs


def get_agent_turns(events: list[StateEvent]) -> list[AgentTurn]:
    turns: list[AgentTurn] = []
    current: AgentTurn | None = None
    pending_tools: dict[str, tuple[ToolCalled, ToolReturned | None]] = {}

    for event in events:
        if isinstance(event, ContextSliced):
            if current is not None:
                current.tool_calls = list(pending_tools.values())
                turns.append(current)
            current = AgentTurn(
                agent_id=event.agent_id,
                workflow_id=event.workflow_id,
                attempt_count=0,
                succeeded=False,
                context_sliced=event,
            )
            pending_tools = {}
            continue

        if current is None:
            continue

        if isinstance(event, PromptAssembled):
            current.prompts.append(event)
            current.attempt_count = max(current.attempt_count, event.attempt_number + 1)
        elif isinstance(event, ModelCalled):
            current.attempt_count = max(current.attempt_count, event.attempt_number + 1)
        elif isinstance(event, ModelReturned):
            for i, (call, ret) in enumerate(current.model_calls):
                if call.call_id == event.call_id:
                    current.model_calls[i] = (call, event)
                    break
            else:
                call = next(
                    (
                        e
                        for e in events
                        if isinstance(e, ModelCalled) and e.call_id == event.call_id
                    ),
                    None,
                )
                if call is not None:
                    current.model_calls.append((call, event))
            current.total_latency_seconds += event.latency_seconds
            current.total_tokens += (event.input_tokens or 0) + (
                event.output_tokens or 0
            )
        elif isinstance(event, ValidationFailed):
            current.validation_failures.append(event)
        elif isinstance(event, ToolCalled):
            pending_tools[event.tool_call_id] = (event, None)
        elif isinstance(event, ToolReturned):
            if event.tool_call_id in pending_tools:
                called, _ = pending_tools[event.tool_call_id]
                pending_tools[event.tool_call_id] = (called, event)
        elif isinstance(event, PatchApplied):
            current.patch_applied = event
            current.succeeded = True
            current.tool_calls = list(pending_tools.values())
            turns.append(current)
            current = None
            pending_tools = {}
        elif isinstance(event, AgentErrored):
            current.succeeded = False
            current.tool_calls = list(pending_tools.values())
            turns.append(current)
            current = None
            pending_tools = {}

    if current is not None:
        current.tool_calls = list(pending_tools.values())
        turns.append(current)

    return turns


def get_turn_for_patch(events: list[StateEvent], patch_id: str) -> AgentTurn | None:
    for turn in get_agent_turns(events):
        if turn.patch_applied is not None and turn.patch_applied.patch_id == patch_id:
            return turn
    return None
