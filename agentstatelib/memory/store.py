from typing import Protocol, runtime_checkable

import aiosqlite

from agentstatelib.core.events import StateEvent, event_adapter


# Protocol : a rule sheet for what a store must be able to do
@runtime_checkable
class StateStore(Protocol):
    """
    Protocol for agentstatelib persistence backends.

    Any class implementing these four async methods satisfies this
    protocol and works as a drop-in backend for AgentGraph.

    No base class import required — structural typing means any
    conforming class qualifies automatically.

    Built-in implementations:
    - InMemoryStore (for testing)
    - SQLiteStore (for single-process use)
    - PostgreSQLStore (for production)
    """

    async def append(self, event: StateEvent) -> None: ...

    async def get_workflow(self, workflow_id: str) -> list[StateEvent]: ...

    async def since(self, workflow_id: str, index: int) -> list[StateEvent]: ...

    async def count(self, workflow_id: str) -> int: ...


class InMemoryStore:
    """
    In-memory StateStore.

    Data is lost when the process exits. Use for tests and rapid
    development.

    Satisfies the StateStore protocol and passes the same test suite
    as SQLiteStore.
    """

    def __init__(self) -> None:
        self._events: dict[str, list[StateEvent]] = {}

    async def append(self, event: StateEvent) -> None:
        """Append an event to the workflow event stream."""

        if event.workflow_id not in self._events:
            self._events[event.workflow_id] = []
        self._events[event.workflow_id].append(event)

    async def get_workflow(self, workflow_id: str) -> list[StateEvent]:
        """Return all events for a workflow."""
        return list(self._events.get(workflow_id, []))

    async def since(self, workflow_id: str, index: int) -> list[StateEvent]:
        """Return events starting at the supplied index."""
        return list(self._events.get(workflow_id, [])[index:])

    async def count(self, workflow_id: str) -> int:
        """Return event count for a workflow."""
        return len(self._events.get(workflow_id, []))


# this method should create the events table if it does not already exists
# create an index on workflow_id
# commit the changes
class SQLiteStore:
    """
    SQLite-backed StateStore.

    Events persist across process restarts. Each write is wrapped in a
    transaction.

    Suitable for single-process workflows and development.

    For production multi-process deployments, use PostgreSQLStore
    (requires asyncpg).
    """

    def __init__(self, path: str) -> None:
        self.path = path

    async def _init_db(self, db: aiosqlite.Connection) -> None:
        """Create required tables and indexes if they do not exist."""

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_wf_id
            ON events(workflow_id)
            """
        )

        await db.commit()

    async def append(self, event: StateEvent) -> None:
        """
        Append an event to persistent storage.
        """
        async with aiosqlite.connect(self.path) as db:
            await self._init_db(db)
            await db.execute(
                """
                INSERT INTO events(event_id, workflow_id, type, data, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.workflow_id,
                    event.type,
                    event.model_dump_json(),
                    event.timestamp,
                ),
            )
            await db.commit()

    async def get_workflow(self, workflow_id: str) -> list[StateEvent]:
        """Return all events for a workflow."""
        async with aiosqlite.connect(self.path) as db:
            await self._init_db(db)
            cursor = await db.execute(
                """
                SELECT data
                FROM events
                WHERE workflow_id=?
                ORDER BY id ASC
                """,
                (workflow_id,),
            )
            rows = await cursor.fetchall()
            return [event_adapter.validate_json(row[0]) for row in rows]

    async def since(self, workflow_id: str, index: int) -> list[StateEvent]:
        """Return events from the given offset onward."""
        async with aiosqlite.connect(self.path) as db:
            await self._init_db(db)
            cursor = await db.execute(
                """
                SELECT data
                FROM events
                WHERE workflow_id=?
                ORDER BY id ASC
                LIMIT -1 OFFSET ?
                """,
                (workflow_id, index),
            )
            rows = await cursor.fetchall()
            return [event_adapter.validate_json(row[0]) for row in rows]

    async def count(self, workflow_id: str) -> int:
        """Return the number of events for a workflow."""
        async with aiosqlite.connect(self.path) as db:
            await self._init_db(db)
            cursor = await db.execute(
                """
                SELECT COUNT(*)
                FROM events
                WHERE workflow_id=?
                """,
                (workflow_id,),
            )
            row = await cursor.fetchone()
            return int(row[0]) if row else 0
