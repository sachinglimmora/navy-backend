import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.scenario import Scenario
from app.models.session import Session as TrainingSession
from app.models.user import User
from app.schemas.base import GenericResponse
from app.schemas.scenario import (
    ScenarioCreate,
    ScenarioGenerateRequest,
    ScenarioList,
    ScenarioOut,
    ScenarioStartRequest,
    ScenarioUpdate,
)
from app.services import ai_service

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


def _extract_json(text: str) -> str:
    """Extract JSON string from potential markdown code blocks."""
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    if "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text.strip()


def _scenario_to_dict(s: Scenario) -> dict:
    return {
        "id": str(s.id),
        "title": s.title,
        "domain": s.domain,
        "difficulty": s.difficulty,
        "doctrine_version": s.doctrine_version,
        "definition": s.definition,
        "created_by": str(s.created_by),
        "estimated_duration_minutes": s.estimated_duration_minutes,
        "tags": s.tags,
        "is_archived": s.is_archived,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


@router.get(
    "",
    response_model=GenericResponse[ScenarioList],
    summary="List Scenarios",
    description=(
        "Retrieve a paginated list of all non-archived training scenarios. "
        "Supports filtering by domain and difficulty level."
    ),
)
async def list_scenarios(
    page: int = Query(1, ge=1, description="Page number to retrieve"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    domain: str | None = Query(
        None, description="Filter by operational domain (e.g., surface, subsurface)"
    ),
    difficulty: str | None = Query(None, description="Filter by scenario difficulty"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List scenarios with optional domain and difficulty filters."""
    query = db.query(Scenario).filter(not Scenario.is_archived)
    if domain:
        query = query.filter(Scenario.domain == domain)
    if difficulty:
        query = query.filter(Scenario.difficulty == difficulty)
    total = query.count()
    scenarios = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "success": True,
        "message": "Scenarios retrieved",
        "data": {
            "items": [_scenario_to_dict(s) for s in scenarios],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post(
    "",
    response_model=GenericResponse[ScenarioOut],
    status_code=201,
    summary="Create Scenario",
    description=(
        "Manually create a new training scenario. "
        "Requires Instructor, Evaluator, or Admin privileges."
    ),
)
async def create_scenario(
    body: ScenarioCreate,
    current_user: User = Depends(require_roles("instructor", "evaluator", "admin")),
    db: Session = Depends(get_db),
):
    """Create a new scenario. Instructor and above."""
    scenario = Scenario(
        id=uuid.uuid4(),
        title=body.title,
        domain=body.domain,
        difficulty=body.difficulty,
        doctrine_version=body.doctrine_version,
        definition=body.definition,
        created_by=current_user.id,
        estimated_duration_minutes=body.estimated_duration_minutes,
        tags=body.tags,
        is_archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return {
        "success": True,
        "message": "Scenario created",
        "data": _scenario_to_dict(scenario),
    }


@router.get(
    "/{scenario_id}",
    response_model=GenericResponse[ScenarioOut],
    summary="Get Scenario Details",
    description="Retrieve full details for a specific scenario by its unique identifier.",
)
async def get_scenario(
    scenario_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single scenario by ID."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {
        "success": True,
        "message": "Scenario retrieved",
        "data": _scenario_to_dict(scenario),
    }


@router.put(
    "/{scenario_id}",
    response_model=GenericResponse[ScenarioOut],
    summary="Update Scenario",
    description=(
        "Modify an existing scenario's parameters. "
        "Requires Instructor, Evaluator, or Admin privileges."
    ),
)
async def update_scenario(
    scenario_id: uuid.UUID,
    body: ScenarioUpdate,
    current_user: User = Depends(require_roles("instructor", "evaluator", "admin")),
    db: Session = Depends(get_db),
):
    """Update a scenario. Instructor and above."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(scenario, field, value)
    scenario.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(scenario)

    return {
        "success": True,
        "message": "Scenario updated",
        "data": _scenario_to_dict(scenario),
    }


@router.delete(
    "/{scenario_id}",
    response_model=GenericResponse[dict],
    summary="Archive Scenario",
    description=(
        "Soft-delete a scenario by marking it as archived. "
        "It will no longer appear in the list."
    ),
)
async def archive_scenario(
    scenario_id: uuid.UUID,
    current_user: User = Depends(require_roles("instructor", "evaluator", "admin")),
    db: Session = Depends(get_db),
):
    """Archive (soft-delete) a scenario. Instructor and above."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    scenario.is_archived = True
    scenario.updated_at = datetime.now(UTC)
    db.commit()

    return {
        "success": True,
        "message": "Scenario archived",
        "data": {"id": str(scenario_id), "is_archived": True},
    }


@router.post(
    "/{scenario_id}/start",
    response_model=GenericResponse[dict],
    status_code=201,
    summary="Start Session from Scenario",
    description="Instantiate a live training session based on this scenario template.",
)
async def start_scenario(
    scenario_id: uuid.UUID,
    body: ScenarioStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Instantiate a training session from this scenario."""
    scenario = (
        db.query(Scenario).filter(Scenario.id == scenario_id, not Scenario.is_archived).first()
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found or archived")

    session = TrainingSession(
        id=uuid.uuid4(),
        scenario_id=scenario_id,
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
        "data": {
            "session_id": str(session.id),
            "scenario_id": str(scenario_id),
            "trainee_id": str(body.trainee_id),
            "status": session.status,
            "started_at": session.started_at.isoformat(),
        },
    }


@router.get(
    "/{scenario_id}/variants",
    response_model=GenericResponse[list[ScenarioOut]],
    summary="Get Scenario Variants",
    description=(
        "List scenarios that share the same domain and similar tags as the "
        "specified scenario."
    ),
)
async def get_variants(
    scenario_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List variants of a scenario (scenarios sharing same domain with similar tags)."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    variants = (
        db.query(Scenario)
        .filter(
            Scenario.domain == scenario.domain,
            Scenario.id != scenario_id,
            not Scenario.is_archived,
        )
        .limit(10)
        .all()
    )
    return {
        "success": True,
        "message": "Variants retrieved",
        "data": [_scenario_to_dict(v) for v in variants],
    }


@router.post(
    "/generate",
    response_model=GenericResponse[ScenarioOut],
    summary="AI-Generate Scenario",
    description=(
        "Use the Ollama LLM to autonomously generate a naval training scenario "
        "based on specified mission parameters."
    ),
)
async def generate_scenario(
    body: ScenarioGenerateRequest,
    current_user: User = Depends(require_roles("instructor", "evaluator", "admin")),
    db: Session = Depends(get_db),
):
    """Use Ollama to AI-generate a scenario definition based on parameters."""
    prompt = (
        f"You are a naval training scenario designer for the Indian Navy. "
        f"Generate a detailed training scenario with the following parameters:\n"
        f"Domain: {body.domain}\n"
        f"Difficulty: {body.difficulty}\n"
        f"Description: {body.description}\n"
        f"Doctrine Version: {body.doctrine_version}\n"
        f"Duration: {body.duration_minutes} minutes\n\n"
        f"Return a JSON scenario definition with keys: title, objectives, "
        f"initial_conditions, events, success_criteria, evaluation_rubric."
    )

    ai_response = await ai_service.generate(prompt)

    # Attempt to parse JSON from response; fall back to plain text definition
    import json as _json

    try:
        cleaned_text = _extract_json(ai_response)
        definition = _json.loads(cleaned_text)
    except Exception:
        definition = {"raw_output": ai_response, "parse_error": True}

    scenario = Scenario(
        id=uuid.uuid4(),
        title=definition.get("title", f"AI-Generated {body.domain.title()} Scenario"),
        domain=body.domain,
        difficulty=body.difficulty,
        doctrine_version=body.doctrine_version,
        definition=definition,
        created_by=current_user.id,
        estimated_duration_minutes=body.duration_minutes,
        tags=["ai-generated", body.domain, body.difficulty],
        is_archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return {
        "success": True,
        "message": "Scenario generated by AI",
        "data": _scenario_to_dict(scenario),
    }
