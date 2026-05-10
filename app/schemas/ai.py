from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime


class ChatMessage(BaseModel):
    role: str  # user|assistant|system
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    session_id: Optional[UUID] = None
    context: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    model: str
    interaction_id: UUID


class AssessRequest(BaseModel):
    session_id: UUID
    trainee_action: str
    expected_action: str
    context: Optional[str] = None
    doctrine_version: Optional[str] = None


class AssessResponse(BaseModel):
    score: float  # 0.0 - 1.0
    feedback: str
    competency_tags: List[str]
    confidence: float
    interaction_id: UUID


class RemediateRequest(BaseModel):
    user_id: UUID
    domain: str
    weakness_description: str
    session_id: Optional[UUID] = None


class RemediateResponse(BaseModel):
    plan: str
    recommended_scenarios: List[str]
    estimated_improvement_sessions: int
    interaction_id: UUID


class HintRequest(BaseModel):
    session_id: UUID
    current_situation: str
    trainee_query: Optional[str] = None


class HintResponse(BaseModel):
    hint: str
    doctrine_reference: Optional[str] = None
    interaction_id: UUID


class AIOverrideRequest(BaseModel):
    interaction_id: UUID
    reason: str
    corrected_response: str


class AuditLogEntry(BaseModel):
    id: UUID
    user_id: UUID
    session_id: Optional[UUID] = None
    interaction_type: str
    doctrine_version_used: Optional[str] = None
    confidence: Optional[float] = None
    overridden_by: Optional[UUID] = None
    override_reason: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class ModelInfo(BaseModel):
    model_name: str
    base_url: str
    status: str
    available: bool
