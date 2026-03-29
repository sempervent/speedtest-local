from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.schemas import PruneRequest, PruneResult
from app.services.app_settings_service import get_app_settings
from app.services.prune_service import prune_older_than

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/prune", response_model=PruneResult)
def admin_prune(
    body: PruneRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> PruneResult:
    if not settings.admin_prune_token:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_PRUNE_TOKEN is not configured on the server",
        )
    if not x_admin_token or x_admin_token != settings.admin_prune_token:
        raise HTTPException(status_code=403, detail="invalid or missing X-Admin-Token")

    app_row = get_app_settings(db, settings)
    days = body.retention_days if body.retention_days is not None else app_row.retention_days
    if days is None:
        raise HTTPException(
            status_code=400,
            detail="retention_days not set on request and app_settings.retention_days is null",
        )

    cutoff, matched, samples_est, runs_del = prune_older_than(
        db, retention_days=days, dry_run=body.dry_run
    )
    if not body.dry_run:
        db.commit()

    return PruneResult(
        dry_run=body.dry_run,
        retention_days_used=days,
        cutoff=cutoff,
        test_runs_matched=matched,
        test_samples_deleted=samples_est if body.dry_run else samples_est,
        test_runs_deleted=runs_del,
    )
