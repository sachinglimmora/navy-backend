import uuid
import hashlib
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.ai_audit import AIAudit
from app.schemas.ai import (
    ChatRequest,
    AssessRequest,
    RemediateRequest,
    HintRequest,
    AIOverrideRequest,
)
from app.dependencies import get_current_user, require_roles
from app.services import ai_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI / LLM"])


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _log_ai_interaction(
    db: Session,
    user_id: uuid.UUID,
    interaction_type: str,
    prompt: str,
    response: str,
    session_id=None,
    confidence: float = None,
    doctrine_version: str = None,
) -> AIAudit:
    audit = AIAudit(
        id=uuid.uuid4(),
        user_id=user_id,
        session_id=session_id,
        prompt_hash=_hash_text(prompt),
        response_hash=_hash_text(response),
        doctrine_version_used=doctrine_version,
        confidence=confidence,
        interaction_type=interaction_type,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(audit)
    db.commit()
    return audit


@router.post("/chat", response_model=dict)
async def ai_chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a chat message to the onboard LLM (Ollama)."""
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    if body.context:
        messages.insert(
            0,
            {
                "role": "system",
                "content": f"Naval Training Context: {body.context}",
            },
        )

    model = body.model or settings.OLLAMA_MODEL
    response_text = await ai_service.chat(messages, model=model)

    prompt_text = " ".join(m["content"] for m in messages)
    audit = _log_ai_interaction(
        db,
        current_user.id,
        "chat",
        prompt_text,
        response_text,
        session_id=body.session_id,
    )

    return {
        "success": True,
        "message": "AI response generated",
        "data": {
            "response": response_text,
            "model": model,
            "interaction_id": str(audit.id),
        },
    }


@router.post("/assess", response_model=dict)
async def ai_assess(
    body: AssessRequest,
    current_user: User = Depends(require_roles("instructor", "evaluator", "admin")),
    db: Session = Depends(get_db),
):
    """Use LLM to score a trainee action against the expected action."""
    prompt = (
        f"You are a naval training evaluator. Score the following trainee action "
        f"against the expected action on a scale of 0.0 to 1.0. "
        f"Respond with JSON: {{\"score\": float, \"feedback\": str, "
        f"\"competency_tags\": [str], \"confidence\": float}}\n\n"
        f"Expected action: {body.expected_action}\n"
        f"Trainee action: {body.trainee_action}\n"
        f"Context: {body.context or 'No additional context'}\n"
        f"Doctrine version: {body.doctrine_version or 'latest'}"
    )

    response_text = await ai_service.generate(prompt)

    import json as _json
    try:
        result = _json.loads(response_text)
        score = float(result.get("score", 0.5))
        feedback = result.get("feedback", response_text)
        competency_tags = result.get("competency_tags", [])
        confidence = float(result.get("confidence", 0.7))
    except Exception:
        score = 0.5
        feedback = response_text
        competency_tags = []
        confidence = 0.5

    audit = _log_ai_interaction(
        db,
        current_user.id,
        "assess",
        prompt,
        response_text,
        session_id=body.session_id,
        confidence=confidence,
        doctrine_version=body.doctrine_version,
    )

    return {
        "success": True,
        "message": "Assessment completed",
        "data": {
            "score": score,
            "feedback": feedback,
            "competency_tags": competency_tags,
            "confidence": confidence,
            "interaction_id": str(audit.id),
        },
    }


@router.post("/remediate", response_model=dict)
async def ai_remediate(
    body: RemediateRequest,
    current_user: User = Depends(require_roles("instructor", "evaluator", "admin")),
    db: Session = Depends(get_db),
):
    """Generate a personalised remediation plan for a trainee's weakness."""
    prompt = (
        f"You are a naval training curriculum designer. Create a remediation plan "
        f"for a trainee with the following weakness:\n"
        f"Domain: {body.domain}\n"
        f"Weakness: {body.weakness_description}\n\n"
        f"Provide a practical remediation plan with recommended exercises, "
        f"estimated number of additional training sessions needed, and specific "
        f"scenarios to practice. Be concise and actionable."
    )

    response_text = await ai_service.generate(prompt)

    audit = _log_ai_interaction(
        db,
        current_user.id,
        "remediate",
        prompt,
        response_text,
        session_id=body.session_id,
    )

    return {
        "success": True,
        "message": "Remediation plan generated",
        "data": {
            "plan": response_text,
            "recommended_scenarios": [
                f"{body.domain}_basic_drill",
                f"{body.domain}_intermediate_exercise",
            ],
            "estimated_improvement_sessions": 3,
            "interaction_id": str(audit.id),
        },
    }


@router.post("/scenario-hint", response_model=dict)
async def ai_scenario_hint(
    body: HintRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Provide a contextual hint for the trainee's current situation."""
    prompt = (
        f"You are a naval training assistant. Provide a helpful hint (not the full answer) "
        f"for the following training situation:\n"
        f"Current situation: {body.current_situation}\n"
        f"Trainee question: {body.trainee_query or 'No specific question'}\n\n"
        f"Give a brief, doctrine-aligned hint that guides without spoiling the exercise."
    )

    response_text = await ai_service.generate(prompt)

    audit = _log_ai_interaction(
        db,
        current_user.id,
        "hint",
        prompt,
        response_text,
        session_id=body.session_id,
    )

    return {
        "success": True,
        "message": "Hint generated",
        "data": {
            "hint": response_text,
            "doctrine_reference": "Naval Training Manual v1.0",
            "interaction_id": str(audit.id),
        },
    }


@router.get("/audit-log", response_model=dict)
async def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    interaction_type: str = None,
    current_user: User = Depends(
        require_roles("evaluator", "fleet", "admin")
    ),
    db: Session = Depends(get_db),
):
    """Return the AI interaction audit trail. Evaluator and above."""
    query = db.query(AIAudit).order_by(AIAudit.timestamp.desc())
    if interaction_type:
        query = query.filter(AIAudit.interaction_type == interaction_type)

    total = query.count()
    entries = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "message": "Audit log retrieved",
        "data": {
            "items": [
                {
                    "id": str(e.id),
                    "user_id": str(e.user_id),
                    "session_id": str(e.session_id) if e.session_id else None,
                    "interaction_type": e.interaction_type,
                    "doctrine_version_used": e.doctrine_version_used,
                    "confidence": e.confidence,
                    "overridden_by": str(e.overridden_by) if e.overridden_by else None,
                    "override_reason": e.override_reason,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in entries
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post("/override", response_model=dict)
async def ai_override(
    body: AIOverrideRequest,
    current_user: User = Depends(require_roles("instructor", "evaluator", "admin")),
    db: Session = Depends(get_db),
):
    """Record an instructor override of an AI decision."""
    audit_entry = db.query(AIAudit).filter(AIAudit.id == body.interaction_id).first()
    if not audit_entry:
        raise HTTPException(status_code=404, detail="AI interaction record not found")

    audit_entry.overridden_by = current_user.id
    audit_entry.override_reason = body.reason
    db.commit()

    return {
        "success": True,
        "message": "AI override recorded",
        "data": {
            "interaction_id": str(body.interaction_id),
            "overridden_by": str(current_user.id),
            "reason": body.reason,
        },
    }


@router.get("/model-info", response_model=dict)
async def get_model_info(
    current_user: User = Depends(get_current_user),
):
    """Return the current LLM model name and Ollama status."""
    status_info = await ai_service.check_ollama_status()
    return {
        "success": True,
        "message": "Model info retrieved",
        "data": {
            "model_name": settings.OLLAMA_MODEL,
            "base_url": settings.OLLAMA_BASE_URL,
            "status": status_info["status"],
            "available": status_info["available"],
            "available_models": status_info.get("models", []),
        },
    }
