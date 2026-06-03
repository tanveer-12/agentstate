from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from agentstatelib.coordination.conflicts import (
    ConflictDetector,
    ConflictRecord,
    ConflictResolver,
    LastWriteWins,
)
from agentstatelib.coordination.invariants import (
    InvariantChecker,
    check_all,
)
from agentstatelib.core.events import (
    ConflictDetected,
    PatchApplied,
    WorkflowCompleted,
    WorkflowStarted,
)
from agentstatelib.core.patch import apply_patch, get_nested
from agentstatelib.core.state import SharedState
from agentstatelib.memory.store import InMemoryStore, StateStore
from agentstatelib.router.context import slice_state
from agentstatelib.router.types import AgentFn, EdgeCondition

# Type Aliases
WorkflowEvent = PatchApplied | WorkflowStarted | WorkflowCompleted | ConflictDetected
EventQueue = asyncio.Queue[WorkflowEvent]


@dataclass(frozen=True)
class _Node:
    agent_id: str
    fn: AgentFn
    context_keys: tuple[str, ...]


@dataclass(frozen=True)
class _Edge:
    from_agent: str
    to_agent: str
    condition: EdgeCondition


class AgentGraph:
    """A directed graph of agents with conditional edges."""

    def __init__(
        self,
        store: StateStore | None = None,
        max_concurrent: int = 3,
        conflict_resolver: ConflictResolver | None = None,
        invariant_checkers: list[InvariantChecker] | None = None,
    ) -> None:
        self._store: StateStore = store or InMemoryStore()
        self._nodes: dict[str, _Node] = {}
        self._edges: list[_Edge] = []
        self._sem = asyncio.Semaphore(max_concurrent)
        resolver = conflict_resolver or LastWriteWins()
        self._conflict_detector = ConflictDetector(resolver)
        self._invariant_checkers: list[InvariantChecker] = invariant_checkers or []

    def node(
        self,
        agent_id: str,
        context: list[str] | None = None,
    ) -> Callable[[AgentFn], AgentFn]:
        """Decorator to register an agent function under a given agent_id"""

        def decorator(fn: AgentFn) -> AgentFn:
            self._nodes[agent_id] = _Node(
                agent_id=agent_id,
                fn=fn,
                context_keys=tuple(context or []),
            )
            return fn

        return decorator

    def edge(
        self,
        from_agent: str,
        to_agent: str,
        condition: EdgeCondition | None = None,
    ) -> None:
        """Add a directed edge between two agents."""
        self._edges.append(
            _Edge(
                from_agent=from_agent,
                to_agent=to_agent,
                condition=condition or (lambda _s: True),
            )
        )

    def _next_agent(self, current_id: str, state_dict: dict) -> str | None:
        """Return the next agent_id to run current_id, or None if done."""

        for edge in self._edges:
            if edge.from_agent != current_id:
                continue
            if edge.condition(state_dict):
                return edge.to_agent

        return None

    def add_invariant(self, checker: InvariantChecker) -> None:
        self._invariant_checkers.append(checker)

    async def run(
        self,
        state: SharedState,
        start: str,
        event_queue: EventQueue | None = None,
    ) -> SharedState:
        """Run the agent graph starting from the given agent_id"""
        if start not in self._nodes:
            raise ValueError(
                f"Start agent '{start}' is not registered in this AgentGraph. "
                f"Registered agents: {list(self._nodes)}"
            )

        # for now, use the state's workflow_id as the workflow identifier
        workflow_id = state.workflow_id

        # Record workflow start
        workflow_started = WorkflowStarted(
            workflow_id=workflow_id,
            agent_id="system",
            workflow_type=state.workflow_type,
            goal=state.goal,
            type="workflow_started",
        )
        await self._store.append(workflow_started)
        if event_queue is not None:
            event_queue.put_nowait(workflow_started)

        self._conflict_detector.reset()
        last_conflict_count = 0

        current_id: str | None = start
        current_state = state

        while current_id is not None:
            if current_id not in self._nodes:
                raise ValueError(
                    f"Agent '{current_id}' is not registered in this AgentGraph. "
                    f"Registered agents: {list(self._nodes)}"
                )

            node = self._nodes[current_id]
            context = slice_state(current_state, list(node.context_keys))

            async with self._sem:
                patch = await node.fn(context)

            winner_patch = self._conflict_detector.submit(patch)

            current_conflicts = self._conflict_detector.conflicts
            if len(current_conflicts) > last_conflict_count:
                new_records: list[ConflictRecord] = current_conflicts[
                    last_conflict_count:
                ]
                for record in new_records:
                    conflict_event = ConflictDetected(
                        workflow_id=workflow_id,
                        agent_id="system",
                        type="conflict_detected",
                        conflict_id=record.conflict_id,
                        path=record.path,
                        winner_agent_id=record.winner_agent_id,
                        loser_agent_id=record.loser_agent_id,
                        resolution_strategy=record.resolution_strategy,
                        existing_patch=record.existing_patch,
                        incoming_patch=record.incoming_patch,
                    )
                    await self._store.append(conflict_event)
                    if event_queue is not None:
                        event_queue.put_nowait(conflict_event)
                last_conflict_count = len(current_conflicts)

            pre_patch_dict = current_state.model_dump()
            old_value = get_nested(pre_patch_dict, winner_patch.target)
            current_state = apply_patch(current_state, winner_patch)
            post_patch_dict = current_state.model_dump()
            new_value = get_nested(post_patch_dict, winner_patch.target)

            self._conflict_detector.mark_applied(winner_patch.target)

            patch_event = PatchApplied(
                workflow_id=workflow_id,
                agent_id=winner_patch.agent_id,
                type="patch_applied",
                patch_id=winner_patch.patch_id,
                target=winner_patch.target,
                old_value=old_value,
                new_value=new_value,
                reason=winner_patch.reason,
                timestamp=winner_patch.timestamp,
            )
            await self._store.append(patch_event)
            if event_queue is not None:
                event_queue.put_nowait(patch_event)

            if self._invariant_checkers:
                violations = check_all(current_state, self._invariant_checkers)
                error_violations = [v for v in violations if v.severity == "error"]
                if error_violations:
                    descriptions = "; ".join(v.description for v in error_violations)
                    raise RuntimeError(
                        f"Invariant violations after patch to '{winner_patch.target}': "
                        f"{descriptions}"
                    )

            current_id = self._next_agent(node.agent_id, post_patch_dict)

        workflow_completed = WorkflowCompleted(
            workflow_id=workflow_id,
            agent_id="system",
            type="workflow_completed",
            final_status=current_state.status,
        )
        await self._store.append(workflow_completed)
        if event_queue is not None:
            event_queue.put_nowait(workflow_completed)

        return current_state
