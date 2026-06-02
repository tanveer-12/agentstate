from __future__ import annotations

from agentstatelib.coordination import (
    ConflictDetector,
    LastWriteWins,
    PriorityBased,
    RejectIncoming,
)
from agentstatelib.core.patch import StatePatch


def test_no_conflict_when_different_paths() -> None:
    detector = ConflictDetector(LastWriteWins())
    p1 = StatePatch(agent_id="a", target="tasks.t1.status", value="done", reason="r1")
    p2 = StatePatch(agent_id="b", target="tasks.t2.status", value="failed", reason="r2")

    detector.submit(p1)
    detector.submit(p2)

    assert len(detector.conflicts) == 0


def test_conflict_detected_on_same_path() -> None:
    detector = ConflictDetector(LastWriteWins())
    p1 = StatePatch(agent_id="a", target="tasks.t1.status", value="done", reason="r1")
    p2 = StatePatch(agent_id="b", target="tasks.t1.status", value="failed", reason="r2")

    detector.submit(p1)
    detector.submit(p2)

    assert len(detector.conflicts) == 1


def test_last_write_wins_returns_newer() -> None:
    detector = ConflictDetector(LastWriteWins())
    p1 = StatePatch(agent_id="a", target="tasks.t1.status", value="done", reason="r1")
    p2 = StatePatch(agent_id="b", target="tasks.t1.status", value="failed", reason="r2")

    # Force timestamps
    p1.timestamp = 1000.0
    p2.timestamp = 2000.0

    detector.submit(p1)
    detector.submit(p2)

    patches = detector.drain()
    assert len(patches) == 1
    winner = patches[0]
    assert winner.agent_id == "b"


def test_priority_based_returns_higher_priority() -> None:
    detector = ConflictDetector(PriorityBased())
    p1 = StatePatch(agent_id="a", target="tasks.t1.status", value="done", reason="r1")
    p2 = StatePatch(agent_id="b", target="tasks.t1.status", value="failed", reason="r2")

    p1.priority = 1
    p2.priority = 10

    detector.submit(p1)
    winner = detector.submit(p2)

    assert winner.agent_id == "b"


def test_reject_incoming_keeps_first() -> None:
    detector = ConflictDetector(RejectIncoming())
    p1 = StatePatch(agent_id="a", target="tasks.t1.status", value="done", reason="r1")
    p2 = StatePatch(agent_id="b", target="tasks.t1.status", value="failed", reason="r2")

    detector.submit(p1)
    winner = detector.submit(p2)

    assert winner.agent_id == "a"


def test_drain_clears_pending() -> None:
    detector = ConflictDetector(LastWriteWins())
    p1 = StatePatch(agent_id="a", target="tasks.t1.status", value="done", reason="r1")
    p2 = StatePatch(agent_id="b", target="tasks.t2.status", value="failed", reason="r2")

    detector.submit(p1)
    detector.submit(p2)

    patches = detector.drain()
    assert len(patches) == 2

    patches_after = detector.drain()
    assert patches_after == []