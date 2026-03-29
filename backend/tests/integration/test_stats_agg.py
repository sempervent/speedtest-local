from datetime import datetime, timedelta, timezone

from app.models import TestRun
from app.services.stats_service import SummaryFilters, compute_summary, compute_timeseries


def test_compute_summary_percentiles(db_session):
    now = datetime.now(timezone.utc)
    for i, v in enumerate([10.0, 20.0, 30.0, 40.0, 50.0]):
        db_session.add(
            TestRun(
                created_at=now - timedelta(minutes=i),
                server_label="default",
                download_mbps=v,
                upload_mbps=v * 0.5,
                latency_ms_avg=2.0,
                jitter_ms=0.2,
                success=True,
            )
        )
    db_session.commit()
    s = compute_summary(db_session, SummaryFilters())
    assert s["count"] == 5
    assert s["download_mbps_p50"] is not None
    assert s["download_mbps_p95"] is not None


def test_compute_timeseries_buckets(db_session):
    now = datetime.now(timezone.utc)
    db_session.add(
        TestRun(
            created_at=now,
            server_label="default",
            download_mbps=100.0,
            upload_mbps=50.0,
            latency_ms_avg=3.0,
            jitter_ms=0.5,
            success=True,
        )
    )
    db_session.commit()
    pts = compute_timeseries(db_session, SummaryFilters(), "day")
    assert len(pts) >= 1
