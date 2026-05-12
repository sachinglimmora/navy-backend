from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    name: str
    status: str  # healthy|degraded|offline
    latency_ms: float | None = None
    details: str | None = None


class HealthMatrix(BaseModel):
    overall: str
    services: list[ServiceStatus]
    checked_at: datetime


class AuditEntry(BaseModel):
    id: str
    timestamp: datetime
    user_id: str
    action: str
    resource: str
    result: str
    ip_address: str | None = None
    details: dict[str, Any] | None = None


class ModelLoadRequest(BaseModel):
    model_name: str
    source_path: str | None = None


class ModelStatus(BaseModel):
    model_name: str
    status: str  # loaded|loading|unavailable
    loaded_at: datetime | None = None
    size_gb: float | None = None
    capabilities: list[str] = []


class BackupRequest(BaseModel):
    include_telemetry: bool = True
    include_doctrine: bool = True
    destination: str | None = None


class SystemMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_sessions: int
    total_users: int
    db_connections: int
    uptime_seconds: float
    collected_at: datetime
