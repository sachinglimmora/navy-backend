import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_all_tables
from app.middleware.rbac import AuditLoggingMiddleware

# Import all routers
from app.routers import (
    auth,
    users,
    scenarios,
    sessions,
    ai,
    analytics,
    certifications,
    digital_twin,
    doctrine,
    system,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup: create database tables if they don't exist."""
    logger.info("GLIMMORA AEGIS backend starting up...")
    try:
        create_all_tables()
        logger.info("Database tables verified/created successfully")
    except Exception as exc:
        logger.error("Failed to create database tables: %s", exc)
    yield
    logger.info("GLIMMORA AEGIS backend shutting down.")


app = FastAPI(
    title="GLIMMORA AEGIS — Navy Training Platform API",
    description=(
        "Air-gapped, sovereign military naval training backend for the Indian Navy. "
        "Supports 7 user roles, 31 training modules, real-time WebSockets, "
        "and AI/LLM integration via Ollama with Qdrant RAG."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — configured from settings; restrict appropriately for air-gapped prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit logging middleware
app.add_middleware(AuditLoggingMiddleware)

# Mount all API routers under /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(certifications.router, prefix="/api")
app.include_router(digital_twin.router, prefix="/api")
app.include_router(doctrine.router, prefix="/api")
app.include_router(system.router, prefix="/api")

# WebSocket routes are already registered inside the session and digital_twin routers


@app.get("/", tags=["Root"])
async def root():
    """Platform root health check endpoint."""
    return {
        "success": True,
        "message": "GLIMMORA AEGIS Navy Training Platform — Backend Operational",
        "data": {
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "docs": "/docs",
        },
    }


@app.get("/health", tags=["Root"])
async def simple_health():
    """Lightweight health probe for load balancers and container orchestration."""
    return {"status": "ok", "service": "aegis-api"}
