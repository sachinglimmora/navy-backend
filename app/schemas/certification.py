from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class CertificationIssue(BaseModel):
    user_id: UUID
    cert_type: str
    domain: str
    valid_until: Optional[datetime] = None
    evidence_session_ids: List[str] = []


class CertificationOut(BaseModel):
    id: UUID
    user_id: UUID
    cert_type: str
    domain: str
    issued_by: UUID
    issued_at: datetime
    valid_until: Optional[datetime] = None
    is_revoked: bool
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[UUID] = None
    evidence_session_ids: List[str]
    certificate_number: str

    model_config = {"from_attributes": True}


class CertificationRevoke(BaseModel):
    reason: str


class CertificationVerify(BaseModel):
    certificate_number: str
    is_valid: bool
    issued_to: str
    issued_to_rank: str
    domain: str
    cert_type: str
    issued_at: datetime
    valid_until: Optional[datetime] = None
    is_revoked: bool
    revoked_reason: Optional[str] = None
