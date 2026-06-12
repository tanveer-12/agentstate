import json
from typing import Any, Protocol, runtime_checkable

import aiosqlite

from agentstatelib.core.events import StateEvent, event_adapter

try:
    import asyncpg

    HAS_ASYNCPG = True
except ImportError:
    asyncpg = None
    HAS_ASYNCPG = False


# Protocol : a rule sheet for what a store must be able to do
@runtime_checkable
class StateStore(Protocol):
    """
    Protocol for agentstatelib persistence backends.

    Any class implementing these five async methods satisfies this
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

    async def list_workflows(self) -> list[str]:
        """Return all unique workflow_ids in the store, most recent first."""
        ...


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

    async def list_workflows(self) -> list[str]:
        """Return all unique workflow_ids in the store, most recent first."""
        return list(reversed(list(self._events.keys())))


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
                schema_version INTEGER NOT NULL DEFAULT 1,
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

        cursor = await db.execute("PRAGMA table_info(events)")
        rows = await cursor.fetchall()
        columns = {row[1] for row in rows}
        if "schema_version" not in columns:
            await db.execute(
                "ALTER TABLE events ADD COLUMN schema_version INTEGER NOT NULL DEFAULT 1"
            )

        await db.commit()

    async def append(self, event: StateEvent) -> None:
        """Append an event to persistent storage."""
        async with aiosqlite.connect(self.path) as db:
            await self._init_db(db)
            await db.execute(
                """
                INSERT INTO events(event_id, workflow_id, type, schema_version, data, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.workflow_id,
                    event.type,
                    getattr(event, "schema_version", 1),
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

    async def list_workflows(self) -> list[str]:
        """Return all unique workflow_ids in the store, most recent first."""
        async with aiosqlite.connect(self.path) as db:
            await self._init_db(db)
            cursor = await db.execute(
                """
                SELECT workflow_id
                FROM events
                GROUP BY workflow_id
                ORDER BY MAX(id) DESC
                """
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


class PostgreSQLStore:
    """
    PostgreSQL-backed StateStore for production multi-process deployments.

    Requires asyncpg: pip install asyncpg.
    DSN format: postgresql://user:password@host/database.
    Connection pool is created lazily on first use. Call close() when done.
    """

    def __init__(self, dsn: str) -> None:
        if not HAS_ASYNCPG:
            raise ImportError(
                "asyncpg required for PostgreSQLStore. "
                "Install with: pip install asyncpg"
            )
        self.dsn = dsn
        self._pool = None

    async def _get_pool(self) -> Any:
        if self._pool is None:
            if asyncpg is None:
                raise ImportError(
                    "asyncpg required for PostgreSQLStore. Install with: pip install asyncpg"
                )
            self._pool = await asyncpg.create_pool(self.dsn)
            await self._init_db()
        return self._pool

    async def _init_db(self) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events(
                        id SERIAL PRIMARY KEY,
                        event_id TEXT NOT NULL,
                        workflow_id TEXT NOT NULL,
                        type TEXT NOT NULL,
                        schema_version INTEGER NOT NULL DEFAULT 1,
                        data TEXT NOT NULL,
                        timestamp DOUBLE PRECISION NOT NULL
                    )
                    """
                )
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_wf_id ON events(workflow_id)"
                )

    async def append(self, workflow_id: str, event: StateEvent) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO events (event_id, workflow_id, type, schema_version, data, timestamp) VALUES ($1, $2, $3, $4, $5, $6)",
                event.event_id,
                workflow_id,
                event.__class__.__name__,
                getattr(event, "schema_version", 1),
                event.model_dump_json(),
                float(event.timestamp),
            )

    async def get_workflow(self, workflow_id: str) -> list[StateEvent]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT data FROM events WHERE workflow_id=$1 ORDER BY id ASC",
                workflow_id,
            )
        return [event_adapter.validate_json(str(row["data"])) for row in rows]

    async def since(self, workflow_id: str, index: int) -> list[StateEvent]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT data FROM events WHERE workflow_id=$1 ORDER BY id ASC OFFSET $2",
                workflow_id,
                index,
            )
        return [event_adapter.validate_json(str(row["data"])) for row in rows]

    async def count(self, workflow_id: str) -> int:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT COUNT(*) FROM events WHERE workflow_id=$1",
                workflow_id,
            )
        return int(row[0]) if row is not None else 0

    async def list_workflows(self) -> list[str]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT workflow_id FROM events GROUP BY workflow_id ORDER BY MAX(id) DESC"
            )
        return [str(row["workflow_id"]) for row in rows]

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
