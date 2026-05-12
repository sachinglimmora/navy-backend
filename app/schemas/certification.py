from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CertificationIssue(BaseModel):
    user_id: UUID
    cert_type: str
    domain: str
    valid_until: datetime | None = None
    evidence_session_ids: list[str] = []


class CertificationOut(BaseModel):
    id: UUID
    user_id: UUID
    cert_type: str
    domain: str
    issued_by: UUID
    issued_at: datetime
    valid_until: datetime | None = None
    is_revoked: bool
    revoked_at: datetime | None = None
    revoked_by: UUID | None = None
    evidence_session_ids: list[str]
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
    valid_until: datetime | None = None
    is_revoked: bool
    revoked_reason: str | None = None
