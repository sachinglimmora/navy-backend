import uuid
import random
import string
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.certification import Certification
from app.schemas.certification import CertificationIssue, CertificationRevoke
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/certifications", tags=["Certifications"])


def _generate_cert_number() -> str:
    """Generate a unique certificate number like AEGIS-2026-XXXX."""
    year = datetime.now().year
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"AEGIS-{year}-{suffix}"


def _cert_to_dict(c: Certification) -> dict:
    return {
        "id": str(c.id),
        "user_id": str(c.user_id),
        "cert_type": c.cert_type,
        "domain": c.domain,
        "issued_by": str(c.issued_by),
        "issued_at": c.issued_at.isoformat(),
        "valid_until": c.valid_until.isoformat() if c.valid_until else None,
        "is_revoked": c.is_revoked,
        "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
        "revoked_by": str(c.revoked_by) if c.revoked_by else None,
        "evidence_session_ids": c.evidence_session_ids,
        "certificate_number": c.certificate_number,
    }


@router.get("/trainee/{user_id}", response_model=dict)
async def list_trainee_certifications(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all certifications for a trainee."""
    if current_user.id != user_id and current_user.role not in (
        "instructor", "evaluator", "fleet", "admin"
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    certs = db.query(Certification).filter(Certification.user_id == user_id).all()
    return {
        "success": True,
        "message": "Certifications retrieved",
        "data": [_cert_to_dict(c) for c in certs],
    }


@router.post("/issue", response_model=dict, status_code=201)
async def issue_certification(
    body: CertificationIssue,
    current_user: User = Depends(require_roles("evaluator", "admin")),
    db: Session = Depends(get_db),
):
    """Issue a new certification to a trainee. Evaluator and above."""
    # Verify the trainee exists
    trainee = db.query(User).filter(User.id == body.user_id, User.is_active == True).first()
    if not trainee:
        raise HTTPException(status_code=404, detail="Trainee not found")

    cert = Certification(
        id=uuid.uuid4(),
        user_id=body.user_id,
        cert_type=body.cert_type,
        domain=body.domain,
        issued_by=current_user.id,
        issued_at=datetime.now(timezone.utc),
        valid_until=body.valid_until,
        is_revoked=False,
        evidence_session_ids=body.evidence_session_ids,
        certificate_number=_generate_cert_number(),
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)

    return {
        "success": True,
        "message": "Certification issued",
        "data": _cert_to_dict(cert),
    }


@router.get("/pending", response_model=dict)
async def get_pending_certifications(
    current_user: User = Depends(require_roles("evaluator", "admin")),
    db: Session = Depends(get_db),
):
    """
    Return candidates eligible for certification review.
    Trainees with completed sessions but no certification in the domain.
    """
    from app.models.session import Session as TrainingSession
    from app.models.scenario import Scenario

    # Get all trainees with completed sessions
    completed_sessions = (
        db.query(TrainingSession)
        .filter(TrainingSession.status == "completed")
        .all()
    )

    # Find trainees without a certification in the session's scenario domain
    pending = []
    seen = set()
    for session in completed_sessions:
        trainee_id = session.trainee_id
        scenario = db.query(Scenario).filter(Scenario.id == session.scenario_id).first()
        if not scenario:
            continue
        key = (trainee_id, scenario.domain)
        if key in seen:
            continue
        seen.add(key)

        has_cert = (
            db.query(Certification)
            .filter(
                Certification.user_id == trainee_id,
                Certification.domain == scenario.domain,
                Certification.is_revoked == False,
            )
            .first()
        )
        if not has_cert:
            trainee = db.query(User).filter(User.id == trainee_id).first()
            if trainee:
                pending.append({
                    "trainee_id": str(trainee_id),
                    "trainee_name": trainee.name,
                    "rank": trainee.rank,
                    "domain": scenario.domain,
                    "completed_session_id": str(session.id),
                    "score": session.score,
                })

    return {
        "success": True,
        "message": "Pending certifications retrieved",
        "data": pending,
    }


@router.get("/{cert_id}/verify", response_model=dict)
async def verify_certification(
    cert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full verification details for a certification."""
    cert = db.query(Certification).filter(Certification.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    trainee = db.query(User).filter(User.id == cert.user_id).first()
    is_valid = (
        not cert.is_revoked
        and (cert.valid_until is None or cert.valid_until > datetime.now(timezone.utc))
    )

    return {
        "success": True,
        "message": "Certification verified",
        "data": {
            "certificate_number": cert.certificate_number,
            "is_valid": is_valid,
            "issued_to": trainee.name if trainee else "Unknown",
            "issued_to_rank": trainee.rank if trainee else "Unknown",
            "domain": cert.domain,
            "cert_type": cert.cert_type,
            "issued_at": cert.issued_at.isoformat(),
            "valid_until": cert.valid_until.isoformat() if cert.valid_until else None,
            "is_revoked": cert.is_revoked,
            "revoked_reason": cert.revoked_by,
        },
    }


@router.put("/{cert_id}/revoke", response_model=dict)
async def revoke_certification(
    cert_id: uuid.UUID,
    body: CertificationRevoke,
    current_user: User = Depends(require_roles("evaluator", "admin")),
    db: Session = Depends(get_db),
):
    """Revoke a certification. Evaluator and above."""
    cert = db.query(Certification).filter(Certification.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    if cert.is_revoked:
        raise HTTPException(status_code=400, detail="Certification already revoked")

    cert.is_revoked = True
    cert.revoked_at = datetime.now(timezone.utc)
    cert.revoked_by = current_user.id
    db.commit()

    return {
        "success": True,
        "message": "Certification revoked",
        "data": _cert_to_dict(cert),
    }
