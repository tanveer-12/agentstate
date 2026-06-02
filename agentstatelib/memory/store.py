from typing import Protocol, runtime_checkable

import aiosqlite

from agentstatelib.core.events import StateEvent, event_adapter


# Protocol : a rule sheet for what a store must be able to do
@runtime_checkable
class StateStore(Protocol):
    async def append(self, event: StateEvent) -> None:
        ...

    async def get_workflow(self, workflow_id: str) -> list[StateEvent]:
        ...

    async def since(self, workflow_id: str, index: int) -> list[StateEvent]:
        ...

    async def count(self, workflow_id: str) -> int:
        ...

class InMemoryStore:
    def __init__(self) -> None:
        self._events: dict[str, list[StateEvent]] = {}

    async def append(self, event: StateEvent) -> None:
        if event.workflow_id not in self._events:
            self._events[event.workflow_id] = []
        self._events[event.workflow_id].append(event)
    
    async def get_workflow(self, workflow_id: str) -> list[StateEvent]:
        return list(self._events.get(workflow_id, []))
    
    async def since(self, workflow_id : str, index: int) -> list[StateEvent]:
        return list(self._events.get(workflow_id, [])[index:])
    
    async def count(self, workflow_id: str) -> int:
        return len(self._events.get(workflow_id, []))

# this method should create the events table if it does not already exists
# create an index on workflow_id
# commit the changes 
class SQLiteStore:
    def __init__(self, path: str) -> None:
        self.path = path
    
    async def _init_db(self, db:aiosqlite.Connection) -> None:
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
    
    async def get_workflow(self, workflow_id : str) -> list[StateEvent]:
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
        