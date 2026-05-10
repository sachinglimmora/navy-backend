from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime


class SessionCreate(BaseModel):
    scenario_id: UUID
    trainee_id: UUID
    instructor_id: Optional[UUID] = None


class SessionOut(BaseModel):
    id: UUID
    scenario_id: UUID
    trainee_id: UUID
    instructor_id: Optional[UUID] = None
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    score: Optional[Dict[str, Any]] = None
    telemetry_log: List[Any]
    replay_ref: Optional[str] = None
    instructor_notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionList(BaseModel):
    items: List[SessionOut]
    total: int


class InjectEvent(BaseModel):
    event_type: str
    payload: Dict[str, Any]
    injected_by: Optional[UUID] = None


class SessionEndRequest(BaseModel):
    instructor_notes: Optional[str] = None
    final_score: Optional[Dict[str, Any]] = None


class TelemetryEntry(BaseModel):
    timestamp: datetime
    event_type: str
    data: Dict[str, Any]
