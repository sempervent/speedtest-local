"""Age-based pruning of test runs (cascades samples)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import TestRun, TestSample


def prune_older_than(
    db: Session,
    *,
    retention_days: int,
    dry_run: bool,
) -> tuple[datetime, int, int, int]:
    """
    Returns (cutoff, matched_runs, samples_deleted, runs_deleted).
    When dry_run, deletion counts are estimates (samples per matched run).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    ids_stmt = select(TestRun.id).where(TestRun.created_at < cutoff)
    ids = [int(i) for i in db.scalars(ids_stmt).all()]
    matched = len(ids)
    if matched == 0:
        return cutoff, 0, 0, 0

    sample_count_stmt = select(func.count()).select_from(TestSample).where(TestSample.test_run_id.in_(ids))
    sample_est = int(db.scalar(sample_count_stmt) or 0)

    if dry_run:
        return cutoff, matched, sample_est, matched

    db.execute(delete(TestSample).where(TestSample.test_run_id.in_(ids)))
    db.execute(delete(TestRun).where(TestRun.id.in_(ids)))
    return cutoff, matched, sample_est, matched
