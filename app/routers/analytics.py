import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.certification import Certification
from app.models.competency import CompetencyRecord
from app.models.session import Session as TrainingSession
from app.models.user import Cohort, User
from app.schemas.analytics import ReportRequest
from app.schemas.base import GenericResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/trainee/{user_id}",
    response_model=GenericResponse[dict],
    summary="Trainee Performance Analytics",
    description=(
        "Retrieve detailed competency records, trends, and session counts for a specific trainee."
    ),
)
async def trainee_analytics(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Competency records for a user, grouped by domain."""
    if current_user.id != user_id and current_user.role not in (
        "instructor",
        "evaluator",
        "fleet",
        "admin",
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    records = db.query(CompetencyRecord).filter(CompetencyRecord.user_id == user_id).all()

    domain_map: dict = {}
    for rec in records:
        if rec.domain not in domain_map:
            domain_map[rec.domain] = {
                "scores": [],
                "skills": {},
                "last_assessed": rec.assessed_at,
            }
        domain_map[rec.domain]["scores"].append(rec.score)
        domain_map[rec.domain]["skills"][rec.skill] = rec.score
        if rec.assessed_at > domain_map[rec.domain]["last_assessed"]:
            domain_map[rec.domain]["last_assessed"] = rec.assessed_at

    domains = []
    for domain, data in domain_map.items():
        avg = sum(data["scores"]) / len(data["scores"])
        # Simple trend: compare first half to second half
        scores = data["scores"]
        if len(scores) >= 4:
            first_half = sum(scores[: len(scores) // 2]) / (len(scores) // 2)
            second_half = sum(scores[len(scores) // 2 :]) / (len(scores) - len(scores) // 2)
            trend = (
                "improving"
                if second_half > first_half
                else ("declining" if second_half < first_half else "stable")
            )
        else:
            trend = "stable"
        domains.append(
            {
                "domain": domain,
                "average_score": round(avg, 2),
                "skill_breakdown": data["skills"],
                "session_count": len(data["scores"]),
                "trend": trend,
                "last_assessed": data["last_assessed"].isoformat(),
            }
        )

    sessions_count = db.query(TrainingSession).filter(TrainingSession.trainee_id == user_id).count()
    certs_count = (
        db.query(Certification)
        .filter(Certification.user_id == user_id, Certification.is_revoked == False)
        .count()
    )

    overall = sum(d["average_score"] for d in domains) / len(domains) if domains else 0.0

    return {
        "success": True,
        "message": "Trainee analytics retrieved",
        "data": {
            "user_id": str(user_id),
            "name": user.name,
            "rank": user.rank,
            "domains": domains,
            "overall_score": round(overall, 2),
            "sessions_completed": sessions_count,
            "certifications_earned": certs_count,
        },
    }


@router.get(
    "/cohort/{cohort_id}",
    response_model=GenericResponse[dict],
    summary="Cohort Aggregated Analytics",
    description=(
        "Aggregate performance data across all members of a training cohort, "
        "identifying top and weakest domains."
    ),
)
async def cohort_analytics(
    cohort_id: uuid.UUID,
    current_user: User = Depends(require_roles("instructor", "evaluator", "fleet", "admin")),
    db: Session = Depends(get_db),
):
    """Cohort performance aggregation."""
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    members = db.query(User).filter(User.cohort_id == cohort_id, User.is_active).all()

    member_summaries = []
    all_scores = []
    for member in members:
        records = db.query(CompetencyRecord).filter(CompetencyRecord.user_id == member.id).all()
        if records:
            avg = sum(r.score for r in records) / len(records)
        else:
            avg = 0.0
        all_scores.append(avg)
        sessions_count = (
            db.query(TrainingSession).filter(TrainingSession.trainee_id == member.id).count()
        )
        member_summaries.append(
            {
                "user_id": str(member.id),
                "name": member.name,
                "rank": member.rank,
                "overall_score": round(avg, 2),
                "sessions_completed": sessions_count,
                "status": "active",
            }
        )

    cohort_avg = sum(all_scores) / len(all_scores) if all_scores else 0.0

    # Domain aggregation
    all_records = (
        db.query(CompetencyRecord)
        .filter(CompetencyRecord.user_id.in_([m.id for m in members]))
        .all()
    )
    domain_scores: dict = {}
    for rec in all_records:
        if rec.domain not in domain_scores:
            domain_scores[rec.domain] = []
        domain_scores[rec.domain].append(rec.score)

    domain_avgs = {d: sum(scores) / len(scores) for d, scores in domain_scores.items()}
    top_domain = max(domain_avgs, key=domain_avgs.get) if domain_avgs else "N/A"
    weakest_domain = min(domain_avgs, key=domain_avgs.get) if domain_avgs else "N/A"

    return {
        "success": True,
        "message": "Cohort analytics retrieved",
        "data": {
            "cohort_id": str(cohort_id),
            "cohort_name": cohort.name,
            "member_count": len(members),
            "average_score": round(cohort_avg, 2),
            "top_domain": top_domain,
            "weakest_domain": weakest_domain,
            "members": member_summaries,
        },
    }


@router.get(
    "/fleet",
    response_model=GenericResponse[dict],
    summary="Fleet-Wide Analytics Summary",
    description=(
        "High-level performance summary for the entire fleet, including active "
        "session counts and certification trends. Restricted to Fleet HQ."
    ),
)
async def fleet_analytics(
    current_user: User = Depends(require_roles("fleet", "admin")),
    db: Session = Depends(get_db),
):
    """Fleet-wide performance summary."""
    total_trainees = db.query(User).filter(User.role == "trainee", User.is_active).count()
    total_sessions = db.query(TrainingSession).count()
    active_sessions = db.query(TrainingSession).filter(TrainingSession.status == "active").count()

    all_records = db.query(CompetencyRecord).all()
    domain_scores: dict = {}
    for rec in all_records:
        if rec.domain not in domain_scores:
            domain_scores[rec.domain] = []
        domain_scores[rec.domain].append(rec.score)

    domain_performance = {d: round(sum(s) / len(s), 2) for d, s in domain_scores.items()}

    fleet_avg = (
        sum(domain_performance.values()) / len(domain_performance) if domain_performance else 0.0
    )

    # Certs issued this month
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    certs_this_month = (
        db.query(Certification).filter(Certification.issued_at >= month_start).count()
    )

    return {
        "success": True,
        "message": "Fleet analytics retrieved",
        "data": {
            "total_trainees": total_trainees,
            "total_sessions": total_sessions,
            "average_fleet_score": round(fleet_avg, 2),
            "domain_performance": domain_performance,
            "certifications_this_month": certs_this_month,
            "active_sessions": active_sessions,
        },
    }


@router.get(
    "/predictive/{user_id}",
    response_model=GenericResponse[dict],
    summary="Predictive Performance Modeling",
    description=(
        "Generate a 30-90 day performance prediction and personalized training "
        "trajectory for a specific trainee."
    ),
)
async def predictive_analytics(
    user_id: uuid.UUID,
    current_user: User = Depends(require_roles("instructor", "evaluator", "fleet", "admin")),
    db: Session = Depends(get_db),
):
    """Simple linear trend prediction from competency history."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    records = (
        db.query(CompetencyRecord)
        .filter(CompetencyRecord.user_id == user_id)
        .order_by(CompetencyRecord.assessed_at)
        .all()
    )

    if len(records) < 2:
        return {
            "success": True,
            "message": "Insufficient data for prediction",
            "data": {
                "user_id": str(user_id),
                "predictions": [],
                "note": "Need at least 2 assessment records for prediction",
            },
        }

    # Group by domain for per-domain prediction
    domain_records: dict = {}
    for rec in records:
        if rec.domain not in domain_records:
            domain_records[rec.domain] = []
        domain_records[rec.domain].append(rec.score)

    predictions = []
    for domain, scores in domain_records.items():
        current = scores[-1]
        if len(scores) >= 2:
            avg_delta = (scores[-1] - scores[0]) / len(scores)
            predicted_30 = min(1.0, max(0.0, current + avg_delta * 3))
            predicted_90 = min(1.0, max(0.0, current + avg_delta * 9))
        else:
            predicted_30 = current
            predicted_90 = current
            avg_delta = 0.0

        trajectory = "positive" if avg_delta > 0.01 else "negative" if avg_delta < -0.01 else "flat"

        recommendations = []
        if current < 0.6:
            recommendations.append(f"Schedule additional {domain} drills")
            recommendations.append("Review relevant doctrine documents")
        elif current < 0.8:
            recommendations.append(f"Practice advanced {domain} scenarios")
        else:
            recommendations.append("Maintain performance with periodic exercises")

        predictions.append(
            {
                "domain": domain,
                "current_score": round(current, 2),
                "predicted_score_30d": round(predicted_30, 2),
                "predicted_score_90d": round(predicted_90, 2),
                "trajectory": trajectory,
                "confidence": 0.65,
                "recommendations": recommendations,
            }
        )

    return {
        "success": True,
        "message": "Predictive analytics generated",
        "data": {
            "user_id": str(user_id),
            "predictions": predictions,
        },
    }


@router.get(
    "/domain/{domain}",
    response_model=GenericResponse[dict],
    summary="Domain Weakness Mapping",
    description=(
        "Analyze performance gaps within a specific operational domain across "
        "all participating personnel."
    ),
)
async def domain_weakness_map(
    domain: str,
    current_user: User = Depends(require_roles("instructor", "evaluator", "fleet", "admin")),
    db: Session = Depends(get_db),
):
    """Domain-wide weakness map showing skill averages."""
    records = db.query(CompetencyRecord).filter(CompetencyRecord.domain == domain).all()

    if not records:
        return {
            "success": True,
            "message": "No data for domain",
            "data": {
                "domain": domain,
                "average_score": 0.0,
                "weakest_skills": [],
                "trainee_count": 0,
            },
        }

    skill_scores: dict = {}
    for rec in records:
        if rec.skill not in skill_scores:
            skill_scores[rec.skill] = []
        skill_scores[rec.skill].append(rec.score)

    skill_avgs = {skill: sum(scores) / len(scores) for skill, scores in skill_scores.items()}
    sorted_skills = sorted(skill_avgs.items(), key=lambda x: x[1])
    weakest = [{"skill": s, "average_score": round(sc, 2)} for s, sc in sorted_skills[:5]]

    domain_avg = sum(skill_avgs.values()) / len(skill_avgs)
    trainee_ids = set(r.user_id for r in records)

    return {
        "success": True,
        "message": "Domain weakness map generated",
        "data": {
            "domain": domain,
            "average_score": round(domain_avg, 2),
            "weakest_skills": weakest,
            "recommended_focus": weakest[0]["skill"] if weakest else "N/A",
            "trainee_count": len(trainee_ids),
        },
    }


@router.post(
    "/report",
    response_model=GenericResponse[dict],
    summary="Generate Analytics Report",
    description=(
        "Export a customized JSON report based on specified filters, domains, "
        "and performance metrics."
    ),
)
async def generate_report(
    body: ReportRequest,
    current_user: User = Depends(require_roles("evaluator", "fleet", "admin")),
    db: Session = Depends(get_db),
):
    """Generate a JSON analytics report."""
    report = {
        "report_type": body.report_type,
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_by": str(current_user.id),
        "parameters": {
            "target_id": str(body.target_id) if body.target_id else None,
            "domain": body.domain,
            "date_from": body.date_from.isoformat() if body.date_from else None,
            "date_to": body.date_to.isoformat() if body.date_to else None,
        },
    }

    if body.report_type == "fleet":
        total_trainees = db.query(User).filter(User.role == "trainee", User.is_active).count()
        total_sessions = db.query(TrainingSession).count()
        report["summary"] = {
            "total_trainees": total_trainees,
            "total_sessions": total_sessions,
        }
    elif body.report_type == "domain" and body.domain:
        records = db.query(CompetencyRecord).filter(CompetencyRecord.domain == body.domain).all()
        report["summary"] = {
            "domain": body.domain,
            "record_count": len(records),
            "average_score": (
                round(sum(r.score for r in records) / len(records), 2) if records else 0.0
            ),
        }
    else:
        report["summary"] = {"note": "Use target_id for trainee/cohort reports"}

    if body.include_recommendations:
        report["recommendations"] = [
            "Increase scenario frequency for underperforming domains",
            "Schedule instructor-led review sessions",
            "Update doctrine documents to reflect current operational requirements",
        ]

    return {
        "success": True,
        "message": "Report generated",
        "data": report,
    }
