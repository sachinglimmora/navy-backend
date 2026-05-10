from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime


class DomainScore(BaseModel):
    domain: str
    average_score: float
    skill_breakdown: Dict[str, float]
    session_count: int
    trend: str  # improving|declining|stable


class TraineeAnalytics(BaseModel):
    user_id: UUID
    name: str
    rank: str
    domains: List[DomainScore]
    overall_score: float
    sessions_completed: int
    certifications_earned: int
    last_activity: Optional[datetime] = None


class CohortMemberSummary(BaseModel):
    user_id: UUID
    name: str
    rank: str
    overall_score: float
    sessions_completed: int
    status: str


class CohortAnalytics(BaseModel):
    cohort_id: UUID
    cohort_name: str
    member_count: int
    average_score: float
    top_domain: str
    weakest_domain: str
    members: List[CohortMemberSummary]


class FleetSummary(BaseModel):
    total_trainees: int
    total_sessions: int
    average_fleet_score: float
    domain_performance: Dict[str, float]
    certifications_this_month: int
    active_sessions: int


class PredictiveTrend(BaseModel):
    user_id: UUID
    domain: str
    current_score: float
    predicted_score_30d: float
    predicted_score_90d: float
    trajectory: str  # positive|negative|flat
    confidence: float
    recommendations: List[str]


class DomainWeaknessMap(BaseModel):
    domain: str
    average_score: float
    weakest_skills: List[Dict[str, Any]]
    recommended_focus: str
    trainee_count: int


class ReportRequest(BaseModel):
    report_type: str  # trainee|cohort|fleet|domain
    target_id: Optional[UUID] = None
    domain: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    include_recommendations: bool = True
