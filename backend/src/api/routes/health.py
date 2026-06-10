"""Health check endpoints."""

import logging

from fastapi import APIRouter
from sqlalchemy import text

from src.database.connection import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    return {"status": "healthy", "service": "earnings-call-analyzer"}


@router.get("/health/ready")
async def readiness_check() -> dict:
    db_status = "unavailable"
    pgvector_status = "unavailable"

    try:
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            if result.scalar() == 1:
                db_status = "connected"

            result = await session.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            )
            if result.scalar():
                pgvector_status = "enabled"
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)

    is_ready = db_status == "connected" and pgvector_status == "enabled"
    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": {"database": db_status, "pgvector": pgvector_status},
    }
