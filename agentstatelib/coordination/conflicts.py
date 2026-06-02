from __future__ import annotations

import time
import uuid
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from agentstatelib.core.patch import StatePatch


class ConflictRecord(BaseModel):
    conflict_id : str = Field(default_factory=lambda: uuid.uuid4().hex)
    path: str
    exisiting_patch: StatePatch
    incoming_patch: StatePatch
    winner_agent_id : str
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
        if incoming.timestamp > existing.timestamp:
            return incoming
        if incoming.timestamp < existing.timestamp:
            return existing
        # if timestamps are equal, prefer incoming
        return incoming
    
class PriorityBased:
    def resolve(self, existing: StatePatch, incoming: StatePatch) -> StatePatch:
        if incoming.priority > existing.priority:
            return incoming
        if incoming.priority < existing.priority:
            return existing
        # if priorities are equal, fall back to last-write-wins
        if incoming.timestamp > existing.timestamp:
            return incoming
        if incoming.timestamp < existing.timestamp:
            return existing 
        return incoming
    
class RejectIncoming:
    """
    Always keeps the first patch received. 
    Incoming patch is logged but not applied.
    """
    def resolve(self, existing: StatePatch, incoming: StatePatch) -> StatePatch:
        return existing
    
class ConflictDetector:
    def __init__(self, resolver: ConflictResolver) -> None:
        self.resolver = resolver
        self._pending: dict[str, StatePatch] = {}
        self._conflicts: list[ConflictRecord] = []
    
    def submit(self, patch: StatePatch) -> StatePatch:
        path = patch.target
        existing = self._pending.get(path)
        if existing is None:
            # No conflicts, just store and return
            self._pending[path] = patch
            return patch
        
        # conflict : existing vs incoming
        winner = self.resolver.resolve(existing, patch)
        loser = patch if winner is existing else existing

        record = ConflictRecord(
            path=path,
            exisiting_patch=existing,
            incoming_patch=patch,
            winner_agent_id=winner.agent_id,
            loser_agent_id=loser.agent_id,
            resolution_strategy=type(self.resolver).__name__,
        )
        self._conflicts.append(record)
        self._pending[path] = winner
        return winner
    
    def drain(self) -> list[StatePatch]:
        patches = list(self._pending.values())
        self._pending.clear()
        return patches
    
    @property
    def conflicts(self) -> list[ConflictRecord]:
        return list(self._conflicts)
    
    def reset(self) -> None:
        self._pending.clear()
        self._conflicts.clear()