from typing import Protocol, runtime_checkable
import aiosqlite
import json
from agentstate.core.events import StateEvent, event_adapter, BaseStateEvent

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

