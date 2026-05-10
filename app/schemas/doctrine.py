from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class DoctrineCreate(BaseModel):
    title: str
    domain: str
    version: str
    content_text: Optional[str] = None
    file_ref: Optional[str] = None


class DoctrineOut(BaseModel):
    id: UUID
    title: str
    domain: str
    version: str
    content_hash: Optional[str] = None
    file_ref: Optional[str] = None
    embedded_at: Optional[datetime] = None
    approved_by: Optional[UUID] = None
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
    last_used: Optional[datetime] = None


class RebuildIndexRequest(BaseModel):
    domain: Optional[str] = None  # None means rebuild all
    force: bool = False
