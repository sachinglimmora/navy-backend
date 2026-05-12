from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DoctrineCreate(BaseModel):
    title: str
    domain: str
    version: str
    content_text: str | None = None
    file_ref: str | None = None


class DoctrineOut(BaseModel):
    id: UUID
    title: str
    domain: str
    version: str
    content_hash: str | None = None
    file_ref: str | None = None
    embedded_at: datetime | None = None
    approved_by: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DoctrineGrounding(BaseModel):
    document_id: UUID
    title: str
    domain: str
    version: str
    usage_count: int
    last_used: datetime | None = None


class RebuildIndexRequest(BaseModel):
    domain: str | None = None  # None means rebuild all
    force: bool = False
