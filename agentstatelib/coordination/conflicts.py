from __future__ import annotations

import time
import uuid
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from agentstatelib.core.patch import StatePatch


class ConflictRecord(BaseModel):
    conflict_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    path: str
    existing_patch: dict[str, object]
    incoming_patch: dict[str, object]
    winner_agent_id: str
    loser_agent_id: str
    resolution_strategy: str
    resolved_at: float = Field(default_factory=time.time)


@runtime_checkable
class ConflictResolver(Protocol):
    def resolve(self, existing: StatePatch, incoming: StatePatch) -> StatePatch:
        """Given an existing patch and an incoming patch,
        return the patch that should be applied.
        """
        ...


class LastWriteWins:
    def resolve(self, existing: StatePatch, incoming: StatePatch) -> StatePatch:
        if incoming.timestamp >= existing.timestamp:
            return incoming
        return existing


class PriorityBased:
    def resolve(self, existing: StatePatch, incoming: StatePatch) -> StatePatch:
        if incoming.priority > existing.priority:
            return incoming
        if incoming.priority < existing.priority:
            return existing
        # Equal priority — fall back to last-write-wins
        if incoming.timestamp >= existing.timestamp:
            return incoming
        return existing


class RejectIncoming:
    """
    Always keeps the first patch received.
    Incoming patch is logged but not applied.
    """

    def resolve(self, existing: StatePatch, incoming: StatePatch) -> StatePatch:
        return existing


# ConflictDetector


class BatchResolutionResult:
    """Result of resolving a batch of patches from one parallel round.

    Attributes
    ----------
    winners:
        The patches that should be applied to state, one per unique path.
        May be fewer than the input if conflicts were resolved.
    conflicts:
        One ConflictRecord for each path collision detected in this batch.
    """

    def __init__(
        self,
        winners: list[StatePatch],
        conflicts: list[ConflictRecord],
    ) -> None:
        self.winners = winners
        self.conflicts = conflicts


class ConflictDetector:
    """Detects and resolves conflicts among patches.

    Designed for parallel execution: resolve_batch() takes all patches
    produced in one parallel round, detects path collisions among them,
    resolves each collision using the configured strategy, and returns
    the winning set.

    Sequential use is also supported via submit() for cases where agents
    run one at a time, but resolve_batch() is preferred for parallel rounds
    because it processes the whole round atomically.

    History
    -------
    All ConflictRecords from the entire workflow run accumulate in
    self._all_conflicts. Call conflicts to read them. Call reset() at
    the start of each new workflow run to clear history.
    """

    def __init__(self, resolver: ConflictResolver) -> None:
        self.resolver = resolver
        self._all_conflicts: list[ConflictRecord] = []

    # ── Primary API for parallel rounds ──────────────────────────────────────

    def resolve_batch(self, patches: list[StatePatch]) -> BatchResolutionResult:
        """Resolve a batch of patches from one parallel execution round.

        For each state path, if more than one patch targets it, the resolver
        picks the winner. All losers are recorded in ConflictRecords.

        Parameters
        ----------
        patches:
            All patches returned by agents that ran in parallel this round.
            Order does not matter — conflicts are resolved by the resolver,
            not by list position.

        Returns
        -------
        BatchResolutionResult
            .winners  — one patch per unique path, ready to apply
            .conflicts — one record per path collision
        """
        # path → current winner for this batch
        winners: dict[str, StatePatch] = {}
        round_conflicts: list[ConflictRecord] = []

        for patch in patches:
            path = patch.target
            existing = winners.get(path)

            if existing is None:
                # First patch to this path in this batch — no conflict yet
                winners[path] = patch
                continue

            # Collision — two agents both targeted this path
            winner = self.resolver.resolve(existing, patch)
            loser = patch if winner is existing else existing

            record = ConflictRecord(
                path=path,
                existing_patch=existing.model_dump(),
                incoming_patch=patch.model_dump(),
                winner_agent_id=winner.agent_id,
                loser_agent_id=loser.agent_id,
                resolution_strategy=type(self.resolver).__name__,
            )
            round_conflicts.append(record)
            self._all_conflicts.append(record)
            winners[path] = winner

        return BatchResolutionResult(
            winners=list(winners.values()),
            conflicts=round_conflicts,
        )

    # ── Sequential compatibility ──────────────────────────────────────────────

    def submit(self, patch: StatePatch) -> tuple[StatePatch, ConflictRecord | None]:
        """Submit a single patch and resolve against the current round's state.

        Convenience wrapper around resolve_batch() for single-patch use.
        Returns (winner_patch, conflict_record_or_none).

        Prefer resolve_batch() when running agents in parallel.
        """
        result = self.resolve_batch([patch])
        conflict = result.conflicts[0] if result.conflicts else None
        return result.winners[0], conflict

    @property
    def conflicts(self) -> list[ConflictRecord]:
        """All conflict records from this workflow run, oldest first."""
        return list(self._all_conflicts)

    def reset(self) -> None:
        """Clear all conflict history for a new workflow run.

        Called automatically by AgentGraph.run() at the start of each run.
        Do not call manually between rounds — history accumulates across
        rounds intentionally so the full run's conflicts are auditable.
        """
        self._all_conflicts.clear()
