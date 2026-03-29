"""Server-side aggregation for summary and time-series stats. Pure helpers are unit-tested."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import and_, func, select, true
from sqlalchemy.orm import Session

from app.models import TestRun

Bucket = Literal["hour", "day", "week", "month"]


@dataclass
class SummaryFilters:
    client_id: int | None = None
    network_label: str | None = None
    server_label: str | None = None
    success: bool | None = None
    from_time: datetime | None = None
    to_time: datetime | None = None


def build_test_run_filter(f: SummaryFilters):
    conds = []
    if f.client_id is not None:
        conds.append(TestRun.client_id == f.client_id)
    if f.network_label:
        conds.append(TestRun.network_label == f.network_label)
    if f.server_label:
        conds.append(TestRun.server_label == f.server_label)
    if f.success is not None:
        conds.append(TestRun.success == f.success)
    if f.from_time is not None:
        conds.append(TestRun.created_at >= f.from_time)
    if f.to_time is not None:
        conds.append(TestRun.created_at <= f.to_time)
    if not conds:
        return true()
    return and_(*conds)


def compute_summary(session: Session, f: SummaryFilters) -> dict[str, Any]:
    flt = build_test_run_filter(f)
    count = session.scalar(select(func.count()).select_from(TestRun).where(flt)) or 0
    if count == 0:
        return {
            "count": 0,
            "download_mbps_avg": None,
            "download_mbps_p50": None,
            "download_mbps_p95": None,
            "upload_mbps_avg": None,
            "upload_mbps_p50": None,
            "upload_mbps_p95": None,
            "latency_ms_avg": None,
            "jitter_ms_avg": None,
        }

    def avg_col(col):
        return session.scalar(
            select(func.avg(col)).select_from(TestRun).where(flt, col.isnot(None))
        )

    def percentile_sql(col: Any, p: float) -> float | None:
        stmt = (
            select(func.percentile_cont(p).within_group(col.asc()))
            .select_from(TestRun)
            .where(flt, col.isnot(None))
        )
        v = session.execute(stmt).scalar()
        return float(v) if v is not None else None

    return {
        "count": int(count),
        "download_mbps_avg": float(a) if (a := avg_col(TestRun.download_mbps)) is not None else None,
        "download_mbps_p50": percentile_sql(TestRun.download_mbps, 0.5),
        "download_mbps_p95": percentile_sql(TestRun.download_mbps, 0.95),
        "upload_mbps_avg": float(a) if (a := avg_col(TestRun.upload_mbps)) is not None else None,
        "upload_mbps_p50": percentile_sql(TestRun.upload_mbps, 0.5),
        "upload_mbps_p95": percentile_sql(TestRun.upload_mbps, 0.95),
        "latency_ms_avg": float(a) if (a := avg_col(TestRun.latency_ms_avg)) is not None else None,
        "jitter_ms_avg": float(a) if (a := avg_col(TestRun.jitter_ms)) is not None else None,
    }


def bucket_trunc_expr(bucket: Bucket):
    trunc = {"hour": "hour", "day": "day", "week": "week", "month": "month"}[bucket]
    return func.date_trunc(trunc, TestRun.created_at)


def compute_timeseries(
    session: Session,
    f: SummaryFilters,
    bucket: Bucket,
    limit_buckets: int = 500,
) -> list[dict[str, Any]]:
    flt = build_test_run_filter(f)
    b = bucket_trunc_expr(bucket)
    stmt = (
        select(
            b.label("bucket_start"),
            func.avg(TestRun.download_mbps).label("download_mbps_avg"),
            func.avg(TestRun.upload_mbps).label("upload_mbps_avg"),
            func.avg(TestRun.latency_ms_avg).label("latency_ms_avg"),
            func.avg(TestRun.jitter_ms).label("jitter_ms_avg"),
            func.count(TestRun.id).label("run_count"),
        )
        .where(flt)
        .group_by(b)
        .order_by(b.asc())
        .limit(limit_buckets)
    )
    rows = session.execute(stmt).all()
    out = []
    for r in rows:
        out.append(
            {
                "bucket_start": r.bucket_start,
                "download_mbps_avg": float(r.download_mbps_avg) if r.download_mbps_avg is not None else None,
                "upload_mbps_avg": float(r.upload_mbps_avg) if r.upload_mbps_avg is not None else None,
                "latency_ms_avg": float(r.latency_ms_avg) if r.latency_ms_avg is not None else None,
                "jitter_ms_avg": float(r.jitter_ms_avg) if r.jitter_ms_avg is not None else None,
                "run_count": int(r.run_count),
            }
        )
    return out


def moving_average(values: list[float | None], window: int) -> list[float | None]:
    """Simple trailing moving average; None values are skipped in the window count."""
    if window < 1:
        raise ValueError("window must be >= 1")
    result: list[float | None] = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_vals = [v for v in values[start : i + 1] if v is not None]
        if not window_vals:
            result.append(None)
        else:
            result.append(sum(window_vals) / len(window_vals))
    return result
