from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class SessionCreate(BaseModel):
    scenario_id: UUID
    trainee_id: UUID
    instructor_id: UUID | None = None


class SessionOut(BaseModel):
    id: UUID
    scenario_id: UUID
    trainee_id: UUID
    instructor_id: UUID | None = None
    status: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    score: dict[str, Any] | None = None
    telemetry_log: list[Any]
    replay_ref: str | None = None
    instructor_notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionList(BaseModel):
    items: list[SessionOut]
    total: int


class InjectEvent(BaseModel):
    event_type: str
    payload: dict[str, Any]
    injected_by: UUID | None = None


class SessionEndRequest(BaseModel):
    instructor_notes: str | None = None
    final_score: dict[str, Any] | None = None


class TelemetryEntry(BaseModel):
    timestamp: datetime
    event_type: str
    data: dict[str, Any]
