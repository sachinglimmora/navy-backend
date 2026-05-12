import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.certification import Certification
from app.models.competency import CompetencyRecord
from app.models.session import Session as TrainingSession
from app.models.user import User
from app.schemas.base import GenericResponse
from app.schemas.user import UserAnalytics, UserCreate, UserList, UserOut, UserUpdate
from app.services.auth_service import hash_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/roles/summary",
    response_model=GenericResponse[dict[str, int]],
    summary="Get Role Distribution",
    description=(
        "Returns a summary of active users grouped by their roles. "
        "Access restricted to Admin and Fleet HQ."
    ),
)
async def get_roles_summary(
    current_user: User = Depends(require_roles("admin", "fleet")),
    db: Session = Depends(get_db),
):
    """Get count of users per role. Admin and fleet only."""
    results = (
        db.query(User.role, func.count(User.id).label("count"))
        .filter(User.is_active)
        .group_by(User.role)
        .all()
    )
    return {
        "success": True,
        "message": "Role summary retrieved",
        "data": {r.role: r.count for r in results},
    }


def _user_to_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "service_number": user.service_number,
        "name": user.name,
        "rank": user.rank,
        "unit": user.unit,
        "role": user.role,
        "cohort_id": str(user.cohort_id) if user.cohort_id else None,
        "classification_clearance": user.classification_clearance,
        "is_active": user.is_active,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


@router.get(
    "",
    response_model=GenericResponse[UserList],
    summary="List All Users",
    description=(
        "Retrieve a paginated list of all personnel. Supports filtering by role. "
        "Access restricted to Admin and Fleet HQ."
    ),
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    role_filter: str | None = Query(None, alias="role", description="Filter by user role"),
    current_user: User = Depends(require_roles("admin", "fleet")),
    db: Session = Depends(get_db),
):
    """List all users with optional role filter. Admin and fleet only."""
    query = db.query(User)
    if role_filter:
        query = query.filter(User.role == role_filter)
    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "success": True,
        "message": "Users retrieved",
        "data": {
            "items": [_user_to_dict(u) for u in users],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post(
    "",
    response_model=GenericResponse[UserOut],
    status_code=201,
    summary="Register New Personnel",
    description="Create a new user profile in the Aegis system. Access restricted to Admin.",
)
async def create_user(
    body: UserCreate,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Create a new user. Admin only."""
    existing = db.query(User).filter(User.service_number == body.service_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service number already registered",
        )

    # Validate cohort_id if provided
    if body.cohort_id:
        from app.models.user import Cohort

        cohort = db.query(Cohort).filter(Cohort.id == body.cohort_id).first()
        if not cohort:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cohort with ID {body.cohort_id} does not exist",
            )

    user = User(
        id=uuid.uuid4(),
        service_number=body.service_number,
        name=body.name,
        rank=body.rank,
        unit=body.unit,
        role=body.role,
        cohort_id=body.cohort_id,
        password_hash=hash_password(body.password),
        classification_clearance=body.classification_clearance,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "success": True,
        "message": "User created",
        "data": _user_to_dict(user),
    }


@router.get(
    "/trainees",
    response_model=GenericResponse[UserList],
    summary="List Active Trainees",
    description=(
        "Retrieve a list of all personnel currently in the 'trainee' role. "
        "Accessible by Instructors and above."
    ),
)
async def list_trainees(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_roles("instructor", "evaluator", "fleet", "admin")),
    db: Session = Depends(get_db),
):
    """List all trainees. Instructor and above."""
    query = db.query(User).filter(User.role == "trainee", User.is_active)
    total = query.count()
    trainees = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "success": True,
        "message": "Trainees retrieved",
        "data": {
            "items": [_user_to_dict(u) for u in trainees],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get(
    "/{user_id}",
    response_model=GenericResponse[UserOut],
    summary="Get User Profile",
    description="Retrieve detailed profile information for a specific user.",
)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user profile. Users can view their own; admins can view any."""
    if current_user.id != user_id and current_user.role not in (
        "admin",
        "fleet",
        "instructor",
        "evaluator",
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {
        "success": True,
        "message": "User retrieved",
        "data": _user_to_dict(user),
    }


@router.patch(
    "/{user_id}",
    response_model=GenericResponse[UserOut],
    summary="Update User Profile",
    description=(
        "Update personnel details. Users can update their own data; "
        "Admins have full write access."
    ),
)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user profile. Users update their own; admins can update any."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = body.model_dump(exclude_unset=True)

    # Validate cohort_id if provided
    if "cohort_id" in update_data and update_data["cohort_id"]:
        from app.models.user import Cohort

        cohort = db.query(Cohort).filter(Cohort.id == update_data["cohort_id"]).first()
        if not cohort:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cohort with ID {update_data['cohort_id']} does not exist",
            )

    # Role changes restricted to admin
    if "role" in update_data and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins may change roles",
        )

    for field, value in update_data.items():
        setattr(user, field, value)
    user.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "User updated",
        "data": _user_to_dict(user),
    }


@router.delete(
    "/{user_id}",
    response_model=GenericResponse[dict],
    summary="Deactivate User Account",
    description="Soft-delete a user profile by marking it as inactive. Access restricted to Admin.",
)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Soft-delete (deactivate) a user. Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = False
    user.updated_at = datetime.now(UTC)
    db.commit()

    return {
        "success": True,
        "message": "User deactivated",
        "data": {"id": str(user_id), "is_active": False},
    }


@router.get(
    "/{user_id}/analytics",
    response_model=GenericResponse[UserAnalytics],
    summary="Get Personnel Analytics",
    description=(
        "Retrieve a comprehensive competency summary, session counts, "
        "and certifications for a specific user."
    ),
)
async def user_analytics(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Competency summary for a user."""
    if current_user.id != user_id and current_user.role not in (
        "admin",
        "fleet",
        "instructor",
        "evaluator",
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Group competency records by domain
    records = db.query(CompetencyRecord).filter(CompetencyRecord.user_id == user_id).all()
    domain_map: dict = {}
    for rec in records:
        if rec.domain not in domain_map:
            domain_map[rec.domain] = {"scores": [], "last_assessed": rec.assessed_at}
        domain_map[rec.domain]["scores"].append(rec.score)
        if rec.assessed_at > domain_map[rec.domain]["last_assessed"]:
            domain_map[rec.domain]["last_assessed"] = rec.assessed_at

    competencies = [
        {
            "domain": domain,
            "average_score": sum(data["scores"]) / len(data["scores"]),
            "skill_count": len(data["scores"]),
            "last_assessed": data["last_assessed"].isoformat(),
        }
        for domain, data in domain_map.items()
    ]

    total_sessions = db.query(TrainingSession).filter(TrainingSession.trainee_id == user_id).count()
    certs_count = (
        db.query(Certification)
        .filter(Certification.user_id == user_id, not Certification.is_revoked)
        .count()
    )

    return {
        "success": True,
        "message": "Analytics retrieved",
        "data": {
            "user_id": str(user_id),
            "name": user.name,
            "rank": user.rank,
            "competencies": competencies,
            "total_sessions": total_sessions,
            "certifications_count": certs_count,
        },
    }
