from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class ServiceStatus(BaseModel):
    name: str
    status: str  # healthy|degraded|offline
    latency_ms: Optional[float] = None
    details: Optional[str] = None


class HealthMatrix(BaseModel):
    overall: str
    services: List[ServiceStatus]
    checked_at: datetime


class AuditEntry(BaseModel):
    id: str
    timestamp: datetime
    user_id: str
    action: str
    resource: str
    result: str
    ip_address: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ModelLoadRequest(BaseModel):
    model_name: str
    source_path: Optional[str] = None


class ModelStatus(BaseModel):
    model_name: str
    status: str  # loaded|loading|unavailable
    loaded_at: Optional[datetime] = None
    size_gb: Optional[float] = None
    capabilities: List[str] = []


class BackupRequest(BaseModel):
    include_telemetry: bool = True
    include_doctrine: bool = True
    destination: Optional[str] = None


class SystemMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_sessions: int
    total_users: int
    db_connections: int
    uptime_seconds: float
    collected_at: datetime
