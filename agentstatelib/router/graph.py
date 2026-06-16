from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from agentstatelib.coordination.conflicts import (
    BatchResolutionResult,
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
    ContextSliced,
    HumanApprovalRequested,
    HumanApprovalResolved,
    PatchApplied,
    WorkflowCompleted,
    WorkflowStarted,
)
from agentstatelib.core.patch import StatePatch, apply_patch, get_nested
from agentstatelib.core.state import SharedState
from agentstatelib.memory.store import InMemoryStore, StateStore
from agentstatelib.observability.tracing import get_tracer
from agentstatelib.router.context import slice_state
from agentstatelib.router.types import AgentFn, EdgeCondition

# Type Aliases
WorkflowEvent = (
    PatchApplied
    | WorkflowStarted
    | WorkflowCompleted
    | ConflictDetected
    | ContextSliced
    | HumanApprovalRequested
    | HumanApprovalResolved
)
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
    approval_required: Callable[[SharedState, StatePatch], bool] | None = None


@dataclass(frozen=True)
class PendingApproval:
    workflow_id: str
    state: SharedState
    patch: StatePatch
    agent_id: str
    description: str


class AgentGraph:
    """Directed graph of agents with round-based parallel execution.

    Execution model
    ---------------
    Each call to run() executes in rounds:

    1. Find all agents whose incoming edges fire given current state.
    2. Run all of them concurrently against the SAME state snapshot.
    3. Collect all their patches.
    4. Resolve path conflicts among the batch using the configured strategy.
    5. Apply winning patches to state, one per unique path.
    6. Emit events for patches and conflicts.
    7. Check invariants on new state.
    8. Repeat from step 1 until no agents are runnable.
    """

    def __init__(
        self,
        store: StateStore | None = None,
        max_concurrent: int = 10,
        conflict_resolver: ConflictResolver | None = None,
        invariant_checkers: list[InvariantChecker] | None = None,
    ) -> None:
        self._store = store if store is not None else InMemoryStore()
        self._nodes: dict[str, _Node] = {}
        self._edges: list[_Edge] = []
        self._sem = asyncio.Semaphore(max_concurrent)
        resolver = conflict_resolver or LastWriteWins()
        self._conflict_detector = ConflictDetector(resolver)
        self._invariant_checkers: list[InvariantChecker] = invariant_checkers or []
        self.pending_approvals: dict[str, PendingApproval] = {}

    def node(
        self,
        agent_id: str,
        context: list[str] | None = None,
    ) -> Callable[[AgentFn], AgentFn]:
        """
        Register an agent node.

        Example:

            @graph.node(
                "planner",
                context=["goal", "tasks"]
            )
            async def planner(ctx):
                ...

        The context list controls which portions of SharedState
        are exposed to the agent.
        """

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
        approval_required: Callable[[SharedState, StatePatch], bool] | None = None,
    ) -> None:
        """
        Add a directed edge from from_agent to to_agent.

        Multiple edges from the same source agent cause all
        reachable agents to be collected and run together in
        the next parallel round.
        """
        self._edges.append(
            _Edge(
                from_agent=from_agent,
                to_agent=to_agent,
                condition=condition or (lambda _s: True),
                approval_required=approval_required,
            )
        )

    def add_invariant(self, checker: InvariantChecker) -> None:
        """
        Register an additional invariant checker.

        Checkers run after every round completes.

        Error-severity violations halt the workflow with
        RuntimeError.
        """
        self._invariant_checkers.append(checker)

    async def run(
        self,
        state: SharedState,
        start: str | list[str],
        event_queue: EventQueue | None = None,
    ) -> SharedState:
        """
        Execute the graph.

        Parameters
        ----------
        state:
            Initial SharedState snapshot.

        start:
            Agent id or list of agent ids to start from.

        event_queue:
            Optional queue receiving workflow events.

        Returns
        -------
        SharedState
            Final workflow state.

        Raises
        ------
        ValueError
            If a start node is not registered.

        RuntimeError
            If invariant checks fail.
        """
        with get_tracer().start_as_current_span("workflow.run") as span:
            start_ids = [start] if isinstance(start, str) else list(start)
            span.set_attribute("workflow.id", state.workflow_id)
            span.set_attribute("workflow.type", state.workflow_type)
            span.set_attribute("workflow.start_agents", str(start_ids))

            for agent_id in start_ids:
                if agent_id not in self._nodes:
                    raise ValueError(
                        f"Start agent '{agent_id}' is not registered in this AgentGraph. "
                        f"Registered agents: {list(self._nodes)}"
                    )

            # for now, use the state's workflow_id as the workflow identifier
            workflow_id = state.workflow_id

            # Emit WorkflowStarted
            await self._emit(
                WorkflowStarted(
                    workflow_id=workflow_id,
                    agent_id="system",
                    workflow_type=state.workflow_type,
                    goal=state.goal,
                ),
                event_queue,
            )
            # Reset conflict history for this run
            self._conflict_detector.reset()
            current_state = state
            current_round_ids = start_ids

            # Round loop
            while current_round_ids:
                current_state = await self._execute_round(
                    agent_ids=current_round_ids,
                    state=current_state,
                    workflow_id=workflow_id,
                    event_queue=event_queue,
                )

                # Compute the next round: all agents reachable from any agent
                # that ran this round, whose edge condition fires on the new state
                current_state_dict = current_state.model_dump()
                current_round_ids = self._next_round(
                    current_round_ids, current_state_dict
                )

            # Emit WorkflowCompleted
            await self._emit(
                WorkflowCompleted(
                    workflow_id=workflow_id,
                    agent_id="system",
                    final_status=current_state.status,
                ),
                event_queue,
            )

            return current_state

    async def _execute_round(
        self,
        agent_ids: list[str],
        state: SharedState,
        workflow_id: str,
        event_queue: EventQueue | None,
    ) -> SharedState:
        """
        Run one round: all agent_ids in parallel against the same state snapshot
        Steps:
        1. Run all agents concurrently — they all read from `state` (the snapshot).
        2. Collect patches.
        3. Resolve conflicts among the batch.
        4. Apply winning patches to state, one per unique path.
        5. Emit PatchApplied and ConflictDetected events.
        6. Run invariant checkers on the fully-updated state.
        7. Return new state.
        """
        with get_tracer().start_as_current_span("round") as span:
            span.set_attribute("round.agent_count", len(agent_ids))
            span.set_attribute("round.agents", str(sorted(agent_ids)))

            patches = await self._run_agents_parallel(agent_ids, state, event_queue)
            result: BatchResolutionResult = self._conflict_detector.resolve_batch(
                patches
            )

            if result.conflicts:
                span.set_attribute("round.conflict_count", len(result.conflicts))

            for record in result.conflicts:
                await self._emit(
                    self._build_conflict_event(workflow_id, record),
                    event_queue,
                )

            pre_round_dict = state.model_dump()
            current_state = state

            for winner_patch in result.winners:
                if self._approval_required_for_patch(current_state, winner_patch):
                    approval_id = str(uuid.uuid4())
                    pending_payload = (
                        winner_patch.model_dump()
                        if hasattr(winner_patch, "model_dump")
                        else dict(winner_patch)
                    )
                    self.pending_approvals[approval_id] = PendingApproval(
                        workflow_id=workflow_id,
                        state=current_state,
                        patch=winner_patch,
                        agent_id=winner_patch.agent_id,
                        description=winner_patch.reason,
                    )
                    await self._emit(
                        HumanApprovalRequested(
                            workflow_id=workflow_id,
                            agent_id=winner_patch.agent_id,
                            approval_id=approval_id,
                            description=winner_patch.reason,
                            pending_patch=pending_payload,
                        ),
                        event_queue,
                    )
                    continue
                old_value = get_nested(pre_round_dict, winner_patch.target)
                current_state = apply_patch(current_state, winner_patch)
                new_value = get_nested(current_state.model_dump(), winner_patch.target)

                await self._emit(
                    PatchApplied(
                        workflow_id=workflow_id,
                        agent_id=winner_patch.agent_id,
                        patch_id=winner_patch.patch_id,
                        target=winner_patch.target,
                        old_value=old_value,
                        new_value=new_value,
                        reason=winner_patch.reason,
                        timestamp=winner_patch.timestamp,
                    ),
                    event_queue,
                )

            # Step 6 — invariant checks run once after all patches in the round
            # are applied, not after each individual patch
            if self._invariant_checkers:
                violations = check_all(current_state, self._invariant_checkers)
                error_violations = [v for v in violations if v.severity == "error"]
                if error_violations:
                    descriptions = "; ".join(v.description for v in error_violations)
                    raise RuntimeError(
                        f"Invariant violations after round [{', '.join(agent_ids)}]: "
                        f"{descriptions}"
                    )

            return current_state

    async def resume_from_approval(
        self,
        approval_id: str,
        decision: Literal["approved", "rejected", "modified"],
        modified_patch: StatePatch | None,
    ) -> SharedState | None:
        """
        Resolve a pending approval and, if approved/modified, apply the patch.

        Returns the updated SharedState when the patch is applied, or None
        when the decision is 'rejected'.

        Raises KeyError if approval_id is not found in pending_approvals.
        Raises ValueError if the decision value is unrecognised.
        """
        pending = self.pending_approvals.pop(approval_id)
        state: SharedState = pending.state
        original_patch: StatePatch = pending.patch
        workflow_id = pending.workflow_id
        patch = modified_patch if modified_patch is not None else original_patch

        await self._emit(
            HumanApprovalResolved(
                workflow_id=workflow_id,
                agent_id="system",
                approval_id=approval_id,
                decision=decision,
            ),
            None,
        )

        if decision in ("approved", "modified"):
            new_state = apply_patch(state, patch)
            await self._emit(
                PatchApplied(
                    workflow_id=workflow_id,
                    agent_id=patch.agent_id,
                    patch_id=patch.patch_id,
                    target=patch.target,
                    old_value=None,
                    new_value=patch.value,
                    reason=patch.reason,
                    timestamp=patch.timestamp,
                ),
                None,
            )
            return new_state
        elif decision == "rejected":
            return None
        else:
            raise ValueError(f"Unknown approval decision: {decision!r}")

    def _approval_required_for_patch(
        self, state: SharedState, patch: StatePatch
    ) -> bool:
        for edge in self._edges:
            if edge.approval_required is None:
                continue
            if edge.approval_required(state, patch):
                return True
        return False

    async def _run_agents_parallel(
        self,
        agent_ids: list[str],
        state: SharedState,
        event_queue: EventQueue | None,
    ) -> list[StatePatch]:
        """Run all agents in agent_ids concurrently against the same state snapshot.

        Each agent receives its configured context slice of `state`.
        All coroutines are gathered — if any raises, the exception propagates
        and the round fails.

        The semaphore limits total concurrency across all rounds.
        """

        async def _call_one(agent_id: str) -> list[StatePatch]:
            with get_tracer().start_as_current_span(f"agent.{agent_id}") as span:
                span.set_attribute("agent.id", agent_id)

                if agent_id not in self._nodes:
                    raise ValueError(
                        f"Agent '{agent_id}' is not registered. "
                        f"Registered agents: {list(self._nodes)}"
                    )
                node = self._nodes[agent_id]
                context = slice_state(state, list(node.context_keys))
                await self._emit(
                    ContextSliced(
                        workflow_id=state.workflow_id,
                        agent_id=agent_id,
                        context_paths=list(node.context_keys),
                        context_size_bytes=len(json.dumps(context, default=str)),
                        snapshot_workflow_id=state.workflow_id,
                    ),
                    event_queue,
                )

                try:
                    async with self._sem:
                        result = await node.fn(context)

                    patches: list[StatePatch]
                    if isinstance(result, StatePatch):
                        patches = [result]
                    else:
                        patches = list(result)
                    span.set_attribute("agent.success", True)
                    span.set_attribute("agent.patch_count", len(patches))
                    return patches
                except Exception as e:
                    span.record_exception(e)
                    span.set_attribute("agent.success", False)
                    raise

        nested = await asyncio.gather(*(_call_one(aid) for aid in agent_ids))

        return [patch for batch in nested for patch in batch]

    # ── Routing ───────────────────────────────────────────────────────────────

    def _next_round(
        self,
        just_ran: list[str],
        state_dict: dict[str, object],
    ) -> list[str]:
        """Compute the set of agents to run in the next round.

        Collects all agents reachable from any agent in just_ran via an edge
        whose condition fires on state_dict. Deduplicates — if two paths lead
        to the same agent, it runs once per round.

        Returns an empty list when no further agents are runnable.
        """
        next_ids: list[str] = []
        seen: set[str] = set()

        for agent_id in just_ran:
            for edge in self._edges:
                if edge.from_agent != agent_id:
                    continue
                if not edge.condition(state_dict):
                    continue
                if edge.to_agent in seen:
                    continue

                seen.add(edge.to_agent)
                next_ids.append(edge.to_agent)

        return next_ids

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _emit(
        self,
        event: WorkflowEvent,
        event_queue: EventQueue | None,
    ) -> None:
        """Append event to the store and optionally put it in the event queue."""
        await self._store.append(event)
        if event_queue is not None:
            event_queue.put_nowait(event)

    @staticmethod
    def _build_conflict_event(
        workflow_id: str,
        record: ConflictRecord,
    ) -> ConflictDetected:
        """Build a ConflictDetected event from a ConflictRecord."""
        return ConflictDetected(
            workflow_id=workflow_id,
            agent_id="system",
            conflict_id=record.conflict_id,
            path=record.path,
            winner_agent_id=record.winner_agent_id,
            loser_agent_id=record.loser_agent_id,
            resolution_strategy=record.resolution_strategy,
            existing_patch=record.existing_patch,
            incoming_patch=record.incoming_patch,
        )
