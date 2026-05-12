from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # user|assistant|system
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None
    session_id: UUID | None = None
    context: str | None = None


class ChatResponse(BaseModel):
    response: str
    model: str
    interaction_id: UUID


class AssessRequest(BaseModel):
    session_id: UUID
    trainee_action: str
    expected_action: str
    context: str | None = None
    doctrine_version: str | None = None


class AssessResponse(BaseModel):
    score: float  # 0.0 - 1.0
    feedback: str
    competency_tags: list[str]
    confidence: float
    interaction_id: UUID


class RemediateRequest(BaseModel):
    user_id: UUID
    domain: str
    weakness_description: str
    session_id: UUID | None = None


class RemediateResponse(BaseModel):
    plan: str
    recommended_scenarios: list[str]
    estimated_improvement_sessions: int
    interaction_id: UUID


class HintRequest(BaseModel):
    session_id: UUID
    current_situation: str
    trainee_query: str | None = None


class HintResponse(BaseModel):
    hint: str
    doctrine_reference: str | None = None
    interaction_id: UUID


class AIOverrideRequest(BaseModel):
    interaction_id: UUID
    reason: str
    corrected_response: str


class AuditLogEntry(BaseModel):
    id: UUID
    user_id: UUID
    session_id: UUID | None = None
    interaction_type: str
    doctrine_version_used: str | None = None
    confidence: float | None = None
    overridden_by: UUID | None = None
    override_reason: str | None = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class ModelInfo(BaseModel):
    model_name: str
    base_url: str
    status: str
    available: bool
