from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

# SQLAlchemy 2.0 synchronous engine (psycopg2)
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=(settings.ENVIRONMENT == "development"),
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    """FastAPI dependency that provides a DB session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    """Create all tables that are registered on the Base metadata."""
    # Import models to ensure they are registered before create_all
    from app.models import (  # noqa: F401
        ai_audit,
        certification,
        competency,
        doctrine,
        notification,
        scenario,
        session,
        user,
    )

    Base.metadata.create_all(bind=engine)
