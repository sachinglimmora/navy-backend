from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UserCreate(BaseModel):
    service_number: str
    name: str
    rank: str
    unit: str
    role: str
    password: str
    cohort_id: UUID | None = None
    classification_clearance: str = "RESTRICTED"


class UserUpdate(BaseModel):
    name: str | None = None
    rank: str | None = None
    unit: str | None = None
    role: str | None = None
    cohort_id: UUID | None = None
    classification_clearance: str | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: UUID
    service_number: str
    name: str
    rank: str
    unit: str
    role: str
    cohort_id: UUID | None = None
    classification_clearance: str
    is_active: bool
    last_login: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserList(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class CompetencySummary(BaseModel):
    domain: str
    average_score: float
    skill_count: int
    last_assessed: datetime | None = None


class UserAnalytics(BaseModel):
    user_id: UUID
    competencies: list[CompetencySummary]
    total_sessions: int
    certifications_count: int
