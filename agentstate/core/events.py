from pydantic import BaseModel, Field, TypeAdapter
from typing import Literal, Annotated, Any, Union
import uuid
import time

# This is the parent all events share
class BaseStateEvent(BaseModel):
    event_id : str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id : str
    agent_id : str
    timestamp : float = Field(default_factory=time.time)


# six subclasses inherting from BaseStateEvent, with each one, having a 'type' field typed as a literal with a single
# string value, and set its default to that string.

class WorkflowStarted(BaseStateEvent):
    type : Literal["workflow_started"]
    workflow_type : str
    goal : str


class WorkflowCompleted(BaseStateEvent):
    type : Literal["workflow_completed"]
    final_status : Any


class PatchApplied(BaseStateEvent):
    type : Literal["patch_applied"]
    patch_id : str
    target : str
    old_value : Any
    new_value : Any
    reason : str


class ConflictDetected(BaseStateEvent):
    type : Literal["conflict_detected"]
    conflict_id : str
    path : str
    winner_agent_id : str
    loser_agent_id : str
    resolution_strategy : str


class CheckpointSaved(BaseStateEvent):
    type : Literal["checkpoint_saved"]
    checkpoint_id : str
    event_count : int

class AgentErrored(BaseStateEvent):
    type : Literal["agent_errored"]
    error_type : str
    error_message : str
    retry_count : int

# Pydantic will use the type field to decide which model to instantiate when deserializing
StateEvent = Annotated[
    Union[
        WorkflowStarted,
        WorkflowCompleted,
        PatchApplied,
        ConflictDetected,
        CheckpointSaved,
        AgentErrored,
    ],
    Field(discriminator="type")
]

# at module level, writing a typeadapter for statevent
# this is how you deserialize a JSON string into the correct event subtype
event_adapter = TypeAdapter(StateEvent)