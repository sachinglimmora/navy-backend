from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
    service_number: str
    name: str
    rank: str
    unit: str
    role: str
    password: str
    cohort_id: Optional[UUID] = None
    classification_clearance: str = "RESTRICTED"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    rank: Optional[str] = None
    unit: Optional[str] = None
    role: Optional[str] = None
    cohort_id: Optional[UUID] = None
    classification_clearance: Optional[str] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    id: UUID
    service_number: str
    name: str
    rank: str
    unit: str
    role: str
    cohort_id: Optional[UUID] = None
    classification_clearance: str
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserList(BaseModel):
    items: List[UserOut]
    total: int
    page: int
    page_size: int


class CompetencySummary(BaseModel):
    domain: str
    average_score: float
    skill_count: int
    last_assessed: Optional[datetime] = None


class UserAnalytics(BaseModel):
    user_id: UUID
    competencies: List[CompetencySummary]
    total_sessions: int
    certifications_count: int
