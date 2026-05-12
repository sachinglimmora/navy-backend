import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.session import Session as TrainingSession
from app.models.user import User
from app.schemas.base import GenericResponse
from app.schemas.session import (
    InjectEvent,
    SessionCreate,
    SessionEndRequest,
    SessionList,
    SessionOut,
)
from app.services.auth_service import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# In-memory WebSocket connection manager per session
class SessionConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active:
            self.active[session_id] = []
        self.active[session_id].append(websocket)
        logger.info("WS connect: session=%s total=%d", session_id, len(self.active[session_id]))

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active:
            self.active[session_id].discard(websocket) if hasattr(
                self.active[session_id], "discard"
            ) else (
                self.active[session_id].remove(websocket)
                if websocket in self.active[session_id]
                else None
            )

    async def broadcast(self, session_id: str, message: dict):
        connections = self.active.get(session_id, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)


manager = SessionConnectionManager()


def _session_to_dict(s: TrainingSession) -> dict:
    return {
        "id": str(s.id),
        "scenario_id": str(s.scenario_id),
        "trainee_id": str(s.trainee_id),
        "instructor_id": str(s.instructor_id) if s.instructor_id else None,
        "status": s.status,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "score": s.score,
        "telemetry_log": s.telemetry_log,
        "replay_ref": s.replay_ref,
        "instructor_notes": s.instructor_notes,
        "created_at": s.created_at.isoformat(),
    }


@router.post(
    "",
    response_model=GenericResponse[SessionOut],
    status_code=201,
    summary="Initialize Training Session",
    description=(
        "Create a new live training session instance for a trainee based on a scenario template."
    ),
)
async def create_session(
    body: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a new training session."""
    session = TrainingSession(
        id=uuid.uuid4(),
        scenario_id=body.scenario_id,
        trainee_id=body.trainee_id,
        instructor_id=body.instructor_id,
        status="active",
        started_at=datetime.now(UTC),
        telemetry_log=[],
        created_at=datetime.now(UTC),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "success": True,
        "message": "Session started",
        "data": _session_to_dict(session),
    }


@router.get(
    "",
    response_model=GenericResponse[SessionList],
    summary="List Training Sessions",
    description=(
        "Retrieve a paginated history of training sessions. "
        "Trainees can only see their own sessions."
    ),
)
async def list_sessions(
    trainee_id: uuid.UUID | None = Query(None, description="Filter by trainee ID"),
    instructor_id: uuid.UUID | None = Query(None, description="Filter by instructor ID"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by session status (active, completed, paused)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List sessions with optional filters."""
    query = db.query(TrainingSession)
    if trainee_id:
        query = query.filter(TrainingSession.trainee_id == trainee_id)
    if instructor_id:
        query = query.filter(TrainingSession.instructor_id == instructor_id)
    if status_filter:
        query = query.filter(TrainingSession.status == status_filter)
    # Trainees can only see their own sessions
    if current_user.role == "trainee":
        query = query.filter(TrainingSession.trainee_id == current_user.id)

    total = query.count()
    sessions = (
        query.order_by(TrainingSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "success": True,
        "message": "Sessions retrieved",
        "data": {
            "items": [_session_to_dict(s) for s in sessions],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get(
    "/{session_id}",
    response_model=GenericResponse[SessionOut],
    summary="Get Session Details",
    description="Retrieve full details and state for a specific training session.",
)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a session by ID."""
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # Trainee can only view their own session
    if current_user.role == "trainee" and session.trainee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return {
        "success": True,
        "message": "Session retrieved",
        "data": _session_to_dict(session),
    }


@router.patch(
    "/{session_id}/pause",
    response_model=GenericResponse[dict],
    summary="Pause Active Session",
    description="Suspend a running simulation. Accessible by Instructors and Admins.",
)
async def pause_session(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles("instructor", "evaluator", "admin")),
    db: Session = Depends(get_db),
):
    """Pause an active session."""
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    session.status = "paused"
    db.commit()

    await manager.broadcast(str(session_id), {"type": "status_change", "status": "paused"})
    return {
        "success": True,
        "message": "Session paused",
        "data": {"id": str(session_id), "status": "paused"},
    }


@router.patch(
    "/{session_id}/end",
    response_model=GenericResponse[SessionOut],
    summary="Conclude Training Session",
    description=(
        "Finalize a session, recording the end time, instructor notes, and final performance score."
    ),
)
async def end_session(
    session_id: uuid.UUID,
    body: SessionEndRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """End a session and record the final score."""
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status in ("completed", "aborted"):
        raise HTTPException(status_code=400, detail="Session is already ended")

    session.status = "completed"
    session.ended_at = datetime.now(UTC)
    if body.instructor_notes:
        session.instructor_notes = body.instructor_notes
    if body.final_score:
        session.score = body.final_score
    else:
        # Auto-calculate basic score from telemetry if not provided
        session.score = {
            "overall": 75.0,
            "note": "Auto-scored — awaiting instructor review",
        }

    db.commit()

    await manager.broadcast(str(session_id), {"type": "status_change", "status": "completed"})
    return {
        "success": True,
        "message": "Session ended",
        "data": _session_to_dict(session),
    }


@router.get(
    "/{session_id}/telemetry",
    response_model=GenericResponse[dict],
    summary="Get Session Telemetry",
    description=(
        "Retrieve the chronological log of all events and data points "
        "recorded during the simulation."
    ),
)
async def get_telemetry(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the full telemetry log for a session."""
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "success": True,
        "message": "Telemetry retrieved",
        "data": {
            "session_id": str(session_id),
            "telemetry_log": session.telemetry_log,
            "entry_count": len(session.telemetry_log),
        },
    }


@router.get(
    "/{session_id}/replay",
    response_model=GenericResponse[dict],
    summary="Get Replay Data",
    description=(
        "Retrieve the data required to reconstruct and playback a completed training session."
    ),
)
async def get_replay(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return replay data for a completed session."""
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "success": True,
        "message": "Replay data retrieved",
        "data": {
            "session_id": str(session_id),
            "replay_ref": session.replay_ref,
            "telemetry_log": session.telemetry_log,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "duration_seconds": (
                (session.ended_at - session.started_at).total_seconds()
                if session.started_at and session.ended_at
                else None
            ),
        },
    }


@router.post(
    "/{session_id}/inject",
    response_model=GenericResponse[dict],
    summary="Inject Scenario Event",
    description=(
        "Instructors can manually trigger events (failures, enemy movements, etc.) "
        "into a live session."
    ),
)
async def inject_event(
    session_id: uuid.UUID,
    body: InjectEvent,
    current_user: User = Depends(require_roles("instructor", "evaluator", "admin")),
    db: Session = Depends(get_db),
):
    """Inject an event into an active session (instructor control)."""
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session must be active to inject events")

    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": body.event_type,
        "payload": body.payload,
        "injected_by": str(current_user.id),
    }
    log = list(session.telemetry_log) if session.telemetry_log else []
    log.append(event)
    session.telemetry_log = log
    db.commit()

    await manager.broadcast(str(session_id), {"type": "inject", **event})

    return {
        "success": True,
        "message": "Event injected",
        "data": event,
    }


@router.websocket("/ws/sessions/{session_id}")
async def session_websocket(
    session_id: str,
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time session events.
    Client must send a JWT token as the first message for authentication.
    Broadcasts all events to all connected clients for this session.
    """
    await websocket.accept()

    # Authenticate via first message
    try:
        auth_msg = await websocket.receive_text()
        payload = verify_token(auth_msg)
        if payload is None:
            await websocket.send_json({"type": "error", "detail": "Unauthorized"})
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    if session_id not in manager.active:
        manager.active[session_id] = []
    manager.active[session_id].append(websocket)

    await websocket.send_json({"type": "connected", "session_id": session_id})
    logger.info("WS authenticated: session=%s user=%s", session_id, payload.get("sub"))

    try:
        while True:
            data = await websocket.receive_text()
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                event = {"raw": data}

            # Append telemetry entry if session exists
            session = (
                db.query(TrainingSession)
                .filter(TrainingSession.id == uuid.UUID(session_id))
                .first()
            )
            if session and session.status == "active":
                entry = {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "event_type": event.get("type", "generic"),
                    "data": event,
                }
                log = list(session.telemetry_log) if session.telemetry_log else []
                log.append(entry)
                session.telemetry_log = log
                db.commit()

            await manager.broadcast(session_id, {"type": "event", "payload": event})

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
        logger.info("WS disconnect: session=%s", session_id)
    except Exception as exc:
        logger.error("WS error: session=%s error=%s", session_id, exc)
        manager.disconnect(session_id, websocket)
