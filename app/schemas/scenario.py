from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime


class ScenarioCreate(BaseModel):
    title: str
    domain: str
    difficulty: str
    doctrine_version: str
    definition: Dict[str, Any] = {}
    estimated_duration_minutes: int = 60
    tags: List[str] = []


class ScenarioUpdate(BaseModel):
    title: Optional[str] = None
    domain: Optional[str] = None
    difficulty: Optional[str] = None
    doctrine_version: Optional[str] = None
    definition: Optional[Dict[str, Any]] = None
    estimated_duration_minutes: Optional[int] = None
    tags: Optional[List[str]] = None
    is_archived: Optional[bool] = None


class ScenarioOut(BaseModel):
    id: UUID
    title: str
    domain: str
    difficulty: str
    doctrine_version: str
    definition: Dict[str, Any]
    created_by: UUID
    estimated_duration_minutes: int
    tags: List[Any]
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScenarioList(BaseModel):
    items: List[ScenarioOut]
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
    instructor_id: Optional[UUID] = None
