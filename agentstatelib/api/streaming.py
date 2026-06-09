import asyncio
from collections.abc import AsyncIterator

from agentstatelib.memory.store import StateStore


async def stream_workflow_events(
    store: StateStore,
    workflow_id: str,
    poll_interval: float = 0.5,
) -> AsyncIterator[str]:
    """
    Async generator yielding Server-Sent Events for a workflow.

    Emits all existing events on connect, then polls every
    poll_interval seconds for new events.

    Maximum stream duration is 5 minutes
    (600 × 0.5s).

    Consumed by GET /v1/workflows/{id}/events.

    The retry directive at the start tells clients to
    reconnect automatically on disconnection.
    """
    yield "retry: 3000\n\n"

    last_count = 0

    for _ in range(600):
        new_events = await store.since(
            workflow_id,
            last_count,
        )

        for event in new_events:
            yield f"data: {event.model_dump_json()}\n\n"

        last_count += len(new_events)

        await asyncio.sleep(poll_interval)
