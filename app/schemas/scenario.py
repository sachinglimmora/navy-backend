from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ScenarioCreate(BaseModel):
    title: str
    domain: str
    difficulty: str
    doctrine_version: str
    definition: dict[str, Any] = {}
    estimated_duration_minutes: int = 60
    tags: list[str] = []


class ScenarioUpdate(BaseModel):
    title: str | None = None
    domain: str | None = None
    difficulty: str | None = None
    doctrine_version: str | None = None
    definition: dict[str, Any] | None = None
    estimated_duration_minutes: int | None = None
    tags: list[str] | None = None
    is_archived: bool | None = None


class ScenarioOut(BaseModel):
    id: UUID
    title: str
    domain: str
    difficulty: str
    doctrine_version: str
    definition: dict[str, Any]
    created_by: UUID
    estimated_duration_minutes: int
    tags: list[Any]
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScenarioList(BaseModel):
    items: list[ScenarioOut]
    total: int
    page: int
    page_size: int


class ScenarioGenerateRequest(BaseModel):
    domain: str
    difficulty: str
    description: str
    doctrine_version: str = "1.0"
    duration_minutes: int = 60


class ScenarioStartRequest(BaseModel):
    trainee_id: UUID
    instructor_id: UUID | None = None
