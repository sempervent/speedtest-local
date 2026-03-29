import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import SessionLocal

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict[str, str]:
    """Process liveness (no DB)."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> JSONResponse:
    """Readiness: database reachable and Alembic head applied."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            ver = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        if not ver:
            return JSONResponse(
                status_code=503,
                content={"status": "degraded", "db": True, "migrations": "unknown"},
            )
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "db": True, "alembic_version": ver},
        )
    except Exception as exc:
        logger.warning("readiness failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "unready", "db": False, "detail": str(exc)},
        )
