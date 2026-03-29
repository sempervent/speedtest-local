"""Explainable regression flags vs a rolling mean of prior successful runs."""

from __future__ import annotations

from statistics import mean
from typing import Literal

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import AnomalyEvent, AppSettings, TestRun

MetricMode = Literal["lower_is_better", "higher_is_better"]

MIN_PRIOR = 3


def _prior_values(
    db: Session,
    *,
    run: TestRun,
    column,
    window: int,
) -> list[float]:
    stmt = (
        select(column)
        .where(
            TestRun.success == True,  # noqa: E712
            TestRun.id != run.id,
            column.isnot(None),
        )
        .order_by(desc(TestRun.created_at))
        .limit(window)
    )
    if run.client_id is not None:
        stmt = stmt.where(TestRun.client_id == run.client_id)
    return [float(v) for v in db.scalars(stmt).all()]


def _severity(deviation_pct: float, threshold_pct: float) -> str:
    if deviation_pct >= threshold_pct * 1.5:
        return "severe"
    return "warn"


def record_anomalies_for_run(db: Session, run: TestRun, app: AppSettings) -> int:
    """Persist anomaly rows for this run. Returns count inserted."""
    if not run.success:
        return 0

    window = app.anomaly_baseline_runs
    thr = app.anomaly_deviation_percent / 100.0
    inserted = 0

    checks: list[tuple[str, MetricMode, float | None]] = [
        ("download_mbps", "lower_is_better", run.download_mbps),
        ("upload_mbps", "lower_is_better", run.upload_mbps),
        ("latency_ms_avg", "higher_is_better", run.latency_ms_avg),
        ("jitter_ms", "higher_is_better", run.jitter_ms),
    ]

    col_map = {
        "download_mbps": TestRun.download_mbps,
        "upload_mbps": TestRun.upload_mbps,
        "latency_ms_avg": TestRun.latency_ms_avg,
        "jitter_ms": TestRun.jitter_ms,
    }

    for name, mode, observed in checks:
        if observed is None:
            continue
        col = col_map[name]
        prior = _prior_values(db, run=run, column=col, window=window)
        if len(prior) < MIN_PRIOR:
            continue
        baseline = mean(prior)
        if baseline <= 0:
            continue

        regresses = False
        if mode == "lower_is_better":
            regresses = observed < baseline * (1 - thr)
            deviation_pct = ((baseline - observed) / baseline) * 100 if regresses else 0.0
        else:
            regresses = observed > baseline * (1 + thr)
            deviation_pct = ((observed - baseline) / baseline) * 100 if regresses else 0.0

        if not regresses:
            continue

        ev = AnomalyEvent(
            test_run_id=run.id,
            client_id=run.client_id,
            metric_name=name,
            baseline_value=baseline,
            observed_value=observed,
            deviation_pct=round(deviation_pct, 4),
            severity=_severity(deviation_pct, app.anomaly_deviation_percent),
            event_meta={"mode": mode, "prior_count": len(prior)},
        )
        db.add(ev)
        inserted += 1

    return inserted
