from pydantic import BaseModel, Field
from typing import Any, Literal
import uuid
import time

WorkflowStatus = Literal["running", "complete", "failed", "paused"]

class Task(BaseModel):
    id : str = Field(default_factory=lambda: str(uuid.uuid4()))
    description : str
    status : Literal["pending", "running", "done", "failed"] = 'pending'
    result : Any | None = 'None'
    created_at : float = Field(default_factory=time.time)
    updated_as: float = Field(default_factory=time.time)


class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description : str
    status : Literal["pending", "active", "complete", "failed"] = 'pending'
    created_at : float = Field(default_factory=time.time)

class Artifact(BaseModel):
    id : str = Field(default_factory=lambda : str(uuid.uuid4()))
    produced_by : str
    artifact_type : str
    content : Any
    created_at : float = Field(default_factory=time.time)

class Decision(BaseModel):
    id : str = Field(default_factory=lambda : str(uuid.uuid4()))
    made_by : str
    description : str
    rationale : str
    timestamp : float = Field(default_factory=time.time)

class SharedState(BaseModel):
    workflow_id : str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_type : str = "general"
    goal : str
    goals : dict[str, Goal] = Field(default_factory=dict)
    tasks : dict[str, Task] = Field(default_factory=dict)
    artifacts : dict[str, Artifact] = Field(default_factory=dict)
    decisions : list[Decision] = Field(default_factory=list)
    facts : dict[str, Any] = Field(default_factory=dict)
    status : WorkflowStatus = 'running' 
    created_at : float = Field(default_factory=time.time)
    updated_at : float = Field(default_factory=time.time)