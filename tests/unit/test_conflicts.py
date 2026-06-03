from __future__ import annotations

from agentstatelib.coordination import (
    BatchResolutionResult,
    ConflictDetector,
    ConflictRecord,
    LastWriteWins,
    PriorityBased,
    RejectIncoming,
)
from agentstatelib.core.patch import StatePatch


def make_patch(agent_id, target, value, timestamp, priority=0):
    return StatePatch(
        agent_id=agent_id,
        target=target,
        value=value,
        reason="test",
        timestamp=timestamp,
        priority=priority,
    )


def test_resolve_batch_no_conflict():
    detector = ConflictDetector(LastWriteWins())
    patches = [
        make_patch("a1", "facts.a", 1, 1000.0),
        make_patch("a2", "facts.b", 2, 1001.0),
    ]
    result = detector.resolve_batch(patches)
    assert len(result.winners) == 2
    assert result.conflicts == []


def test_resolve_batch_detects_collision():
    detector = ConflictDetector(LastWriteWins())
    patches = [
        make_patch("a1", "facts.a", 1, 1000.0),
        make_patch("a2", "facts.a", 2, 1001.0),
    ]
    result = detector.resolve_batch(patches)
    assert len(result.conflicts) == 1
    assert len(result.winners) == 1


def test_resolve_batch_last_write_wins():
    detector = ConflictDetector(LastWriteWins())
    older = make_patch("a1", "facts.a", 1, 1000.0)
    newer = make_patch("a2", "facts.a", 2, 2000.0)
    result = detector.resolve_batch([older, newer])
    assert len(result.winners) == 1
    assert result.winners[0].agent_id == "a2"
    assert result.winners[0].timestamp == 2000.0


def test_resolve_batch_priority_based():
    detector = ConflictDetector(PriorityBased())
    low = make_patch("a1", "facts.a", 1, 1000.0, priority=1)
    high = make_patch("a2", "facts.a", 2, 1001.0, priority=10)
    result = detector.resolve_batch([low, high])
    assert len(result.winners) == 1
    assert result.winners[0].agent_id == "a2"
    assert result.winners[0].priority == 10


def test_resolve_batch_reject_incoming():
    detector = ConflictDetector(RejectIncoming())
    first = make_patch("a1", "facts.a", 1, 1000.0)
    second = make_patch("a2", "facts.a", 2, 2000.0)
    result = detector.resolve_batch([first, second])
    assert len(result.winners) == 1
    assert result.winners[0].agent_id == "a1"


def test_resolve_batch_three_patches_same_path():
    detector = ConflictDetector(LastWriteWins())
    patches = [
        make_patch("a1", "facts.a", 1, 1000.0),
        make_patch("a2", "facts.a", 2, 2000.0),
        make_patch("a3", "facts.a", 3, 3000.0),
    ]
    result = detector.resolve_batch(patches)
    assert len(result.winners) == 1
    assert len(result.conflicts) == 2
    assert result.winners[0].agent_id == "a3"
    assert result.winners[0].timestamp == 3000.0


def test_submit_returns_tuple():
    detector = ConflictDetector(LastWriteWins())
    patch = make_patch("a1", "facts.a", 1, 1000.0)
    winner, conflict = detector.submit(patch)
    assert isinstance(winner, StatePatch)
    assert conflict is None
    assert winner.agent_id == "a1"


def test_conflicts_accumulate_across_batches():
    detector = ConflictDetector(LastWriteWins())

    detector.resolve_batch(
        [
            make_patch("a1", "facts.a", 1, 1000.0),
            make_patch("a2", "facts.a", 2, 2000.0),
        ]
    )
    detector.resolve_batch(
        [
            make_patch("b1", "facts.b", 1, 1000.0),
            make_patch("b2", "facts.b", 2, 2000.0),
        ]
    )

    assert len(detector.conflicts) == 2
    detector.reset()
    assert len(detector.conflicts) == 0
