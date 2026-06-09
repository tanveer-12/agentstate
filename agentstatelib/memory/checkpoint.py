from __future__ import annotations

import time
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from agentstatelib.core.state import SharedState
from agentstatelib.memory.store import StateStore


class Checkpoint(BaseModel):
    """
    A snapshot of SharedState at a point in time.
    event_count marks where in the event log the workflow had progressed, so recovery
    can resume from the store without replaying the entire history from scratch.
    """

    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    state: SharedState
    event_count: int
    created_at: float = Field(default_factory=time.time)


async def save_checkpoint(
    state: SharedState,
    store: StateStore,
    directory: str = ".checkpoints",
) -> Checkpoint:
    Path(directory).mkdir(parents=True, exist_ok=True)
    count = await store.count(state.workflow_id)
    checkpoint = Checkpoint(
        workflow_id=state.workflow_id,
        state=state,
        event_count=count,
    )
    path = Path(directory) / f"{state.workflow_id}_{checkpoint.checkpoint_id}.json"
    path.write_text(checkpoint.model_dump_json())
    return checkpoint


def load_latest_checkpoint(
    workflow_id: str,
    directory: str = ".checkpoints",
) -> Checkpoint | None:
    files = list(Path(directory).glob(f"{workflow_id}_*.json"))
    if not files:
        return None
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return Checkpoint.model_validate_json(files[0].read_text())


def load_checkpoint(
    checkpoint_id: str,
    directory: str = ".checkpoints",
) -> Checkpoint:
    matches = list(Path(directory).glob(f"*_{checkpoint_id}.json"))
    if not matches:
        raise FileNotFoundError(
            f"Checkpoint {checkpoint_id!r} not found in {directory!r}"
        )
    return Checkpoint.model_validate_json(matches[0].read_text())
