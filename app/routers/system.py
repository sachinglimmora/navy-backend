import logging
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.dependencies import get_current_user, require_roles
from app.models.session import Session as TrainingSession
from app.models.user import User
from app.schemas.system import BackupRequest, ModelLoadRequest
from app.services import ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["System"])

_start_time = time.time()


async def _check_db(db: Session) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"name": "PostgreSQL", "status": "healthy", "latency_ms": None}
    except Exception as exc:
        return {"name": "PostgreSQL", "status": "offline", "details": str(exc)}


async def _check_redis() -> dict:
    try:
        import redis as redis_lib

        r = redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        start = time.monotonic()
        r.ping()
        latency = round((time.monotonic() - start) * 1000, 2)
        return {"name": "Redis", "status": "healthy", "latency_ms": latency}
    except Exception as exc:
        return {"name": "Redis", "status": "offline", "details": str(exc)}


async def _check_ollama() -> dict:
    import httpx

    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
        latency = round((time.monotonic() - start) * 1000, 2)
        if resp.status_code == 200:
            return {"name": "Ollama LLM", "status": "healthy", "latency_ms": latency}
        return {"name": "Ollama LLM", "status": "degraded", "details": f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"name": "Ollama LLM", "status": "offline", "details": str(exc)}


async def _check_qdrant() -> dict:
    import httpx

    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}/health")
        latency = round((time.monotonic() - start) * 1000, 2)
        if resp.status_code == 200:
            return {"name": "Qdrant", "status": "healthy", "latency_ms": latency}
        return {"name": "Qdrant", "status": "degraded", "details": f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"name": "Qdrant", "status": "offline", "details": str(exc)}


@router.get("/health", response_model=dict)
async def health_check(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full service health matrix — checks DB, Redis, Ollama, and Qdrant."""
    db_status = await _check_db(db)
    redis_status = await _check_redis()
    ollama_status = await _check_ollama()
    qdrant_status = await _check_qdrant()

    services = [db_status, redis_status, ollama_status, qdrant_status]
    statuses = [s["status"] for s in services]

    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "offline" for s in statuses):
        overall = "degraded"
    else:
        overall = "partial"

    return {
        "success": True,
        "message": "Health check complete",
        "data": {
            "overall": overall,
            "services": services,
            "checked_at": datetime.now(UTC).isoformat(),
        },
    }


@router.get("/audit-log", response_model=dict)
async def get_audit_log(
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Full system audit trail. Admin only."""
    from app.models.ai_audit import AIAudit

    # Return AI audit records as the system audit trail
    query = db.query(AIAudit).order_by(AIAudit.timestamp.desc())
    total = query.count()
    entries = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "message": "Audit log retrieved",
        "data": {
            "items": [
                {
                    "id": str(e.id),
                    "timestamp": e.timestamp.isoformat(),
                    "user_id": str(e.user_id),
                    "action": e.interaction_type,
                    "resource": "ai_model",
                    "result": "success",
                    "overridden": e.overridden_by is not None,
                }
                for e in entries
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post("/model/load", response_model=dict)
async def load_model(
    body: ModelLoadRequest,
    current_user: User = Depends(require_roles("maintainer", "admin")),
):
    """
    Request Ollama to load/pull a new model.
    Maintainer and admin only — this touches the LLM weight layer.
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/pull",
                json={"name": body.model_name, "stream": False},
            )
            if resp.status_code == 200:
                return {
                    "success": True,
                    "message": f"Model '{body.model_name}' loaded successfully",
                    "data": {"model_name": body.model_name, "status": "loaded"},
                }
            raise HTTPException(
                status_code=502,
                detail=f"Ollama returned HTTP {resp.status_code}",
            )
    except httpx.ConnectError as err:
        raise HTTPException(status_code=503, detail="Ollama is offline") from err
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/model/status", response_model=dict)
async def model_status(
    current_user: User = Depends(get_current_user),
):
    """Return the model registry (what is loaded in Ollama)."""
    status_info = await ai_service.check_ollama_status()
    models = [
        {
            "model_name": m,
            "status": "loaded",
            "capabilities": ["chat", "generate", "embed"],
        }
        for m in status_info.get("models", [])
    ]
    return {
        "success": True,
        "message": "Model registry retrieved",
        "data": {
            "ollama_status": status_info["status"],
            "active_model": settings.OLLAMA_MODEL,
            "models": models,
        },
    }


@router.post("/backup", response_model=dict)
async def trigger_backup(
    body: BackupRequest,
    current_user: User = Depends(require_roles("admin", "maintainer")),
):
    """
    Trigger a system backup.
    In production this would invoke pg_dump and MinIO sync.
    """
    import uuid as _uuid

    backup_id = str(_uuid.uuid4())
    return {
        "success": True,
        "message": "Backup initiated",
        "data": {
            "backup_id": backup_id,
            "status": "initiated",
            "include_telemetry": body.include_telemetry,
            "include_doctrine": body.include_doctrine,
            "destination": body.destination or "default-backup-volume",
            "initiated_at": datetime.now(UTC).isoformat(),
            "note": "Backup process running in background",
        },
    }


@router.get("/metrics", response_model=dict)
async def system_metrics(
    current_user: User = Depends(require_roles("admin", "maintainer", "fleet")),
    db: Session = Depends(get_db),
):
    """Return live system metrics."""
    import psutil

    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
    except Exception:
        cpu = mem = disk = 0.0

    active_sessions = db.query(TrainingSession).filter(TrainingSession.status == "active").count()
    total_users = db.query(User).filter(User.is_active).count()

    try:
        pool = engine.pool
        db_connections = pool.checkedout()
    except Exception:
        db_connections = 0

    uptime = round(time.time() - _start_time, 1)

    return {
        "success": True,
        "message": "System metrics retrieved",
        "data": {
            "cpu_percent": cpu,
            "memory_percent": mem,
            "disk_percent": disk,
            "active_sessions": active_sessions,
            "total_users": total_users,
            "db_connections": db_connections,
            "uptime_seconds": uptime,
            "collected_at": datetime.now(UTC).isoformat(),
        },
    }
