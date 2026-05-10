"""Initial schema — all tables

Revision ID: 001
Revises:
Create Date: 2026-05-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- cohorts ---
    op.create_table(
        "cohorts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("fleet_id", sa.String(100), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("service_number", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("rank", sa.String(50), nullable=False),
        sa.Column("unit", sa.String(200), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column(
            "cohort_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cohorts.id"),
            nullable=True,
        ),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column(
            "classification_clearance", sa.String(50), server_default="RESTRICTED"
        ),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_service_number", "users", ["service_number"])
    op.create_index("ix_users_role", "users", ["role"])

    # --- scenarios ---
    op.create_table(
        "scenarios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("domain", sa.String(100), nullable=False),
        sa.Column("difficulty", sa.String(50), nullable=False),
        sa.Column("doctrine_version", sa.String(50), nullable=False),
        sa.Column("definition", JSONB, nullable=False),
        sa.Column(
            "created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("estimated_duration_minutes", sa.Integer, server_default="60"),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("is_archived", sa.Boolean, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_scenarios_domain", "scenarios", ["domain"])
    op.create_index("ix_scenarios_difficulty", "scenarios", ["difficulty"])

    # --- sessions ---
    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "scenario_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scenarios.id"),
            nullable=False,
        ),
        sa.Column(
            "trainee_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "instructor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", JSONB, nullable=True),
        sa.Column("telemetry_log", JSONB, server_default="[]"),
        sa.Column("replay_ref", sa.String(500), nullable=True),
        sa.Column("instructor_notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_sessions_scenario_id", "sessions", ["scenario_id"])
    op.create_index("ix_sessions_trainee_id", "sessions", ["trainee_id"])
    op.create_index("ix_sessions_status", "sessions", ["status"])

    # --- competency_records ---
    op.create_table(
        "competency_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("domain", sa.String(100), nullable=False),
        sa.Column("skill", sa.String(200), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("evidence", JSONB, server_default="{}"),
        sa.Column(
            "assessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sessions.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_competency_records_user_id", "competency_records", ["user_id"])
    op.create_index("ix_competency_records_domain", "competency_records", ["domain"])

    # --- certifications ---
    op.create_table(
        "certifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("cert_type", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(100), nullable=False),
        sa.Column(
            "issued_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_revoked", sa.Boolean, server_default="false"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "revoked_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("evidence_session_ids", JSONB, server_default="[]"),
        sa.Column("certificate_number", sa.String(100), nullable=False, unique=True),
    )
    op.create_index("ix_certifications_user_id", "certifications", ["user_id"])

    # --- ai_audit ---
    op.create_table(
        "ai_audit",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sessions.id"),
            nullable=True,
        ),
        sa.Column("prompt_hash", sa.String(64), nullable=False),
        sa.Column("response_hash", sa.String(64), nullable=False),
        sa.Column("doctrine_version_used", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column(
            "overridden_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("override_reason", sa.Text, nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("interaction_type", sa.String(100), nullable=False),
    )
    op.create_index("ix_ai_audit_user_id", "ai_audit", ["user_id"])
    op.create_index("ix_ai_audit_timestamp", "ai_audit", ["timestamp"])

    # --- doctrine_docs ---
    op.create_table(
        "doctrine_docs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("domain", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("file_ref", sa.String(500), nullable=True),
        sa.Column("content_text", sa.Text, nullable=True),
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "approved_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_doctrine_docs_domain", "doctrine_docs", ["domain"])

    # --- notifications ---
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("is_read", sa.Boolean, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("doctrine_docs")
    op.drop_table("ai_audit")
    op.drop_table("certifications")
    op.drop_table("competency_records")
    op.drop_table("sessions")
    op.drop_table("scenarios")
    op.drop_table("users")
    op.drop_table("cohorts")
