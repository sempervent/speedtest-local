from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.models import AppSettings, SamplePhase, TestRun, TestSample
from app.schemas import TestRunCreate
from app.services.client_service import parse_ua_simple, upsert_client_from_test


def create_test_run(
    db: Session,
    payload: TestRunCreate,
    *,
    app_settings: AppSettings,
    env_settings: Settings,
    ip_address: str | None,
) -> TestRun:
    _ = env_settings  # reserved for future caps enforced server-side on payload
    hints = parse_ua_simple(payload.browser_user_agent)
    client = upsert_client_from_test(
        db,
        stable_id=payload.client_stable_id,
        label=payload.client_label,
        network_label=payload.network_label,
        browser_user_agent=payload.browser_user_agent,
        parse_hints=hints,
    )
    server_label = payload.server_label or app_settings.server_label
    now = datetime.now(timezone.utc)
    run = TestRun(
        started_at=payload.started_at,
        completed_at=payload.completed_at or now,
        client_id=client.id if client else None,
        client_label=payload.client_label,
        server_label=server_label,
        latency_ms_avg=payload.latency_ms_avg,
        jitter_ms=payload.jitter_ms,
        download_mbps=payload.download_mbps,
        upload_mbps=payload.upload_mbps,
        packet_loss_pct=payload.packet_loss_pct,
        download_bytes_total=payload.download_bytes_total,
        upload_bytes_total=payload.upload_bytes_total,
        duration_seconds=payload.duration_seconds,
        success=payload.success,
        failure_reason=payload.failure_reason,
        raw_metrics_json=payload.raw_metrics_json,
        browser_user_agent=payload.browser_user_agent,
        ip_address=ip_address,
        notes=payload.notes,
        network_label=payload.network_label,
    )
    db.add(run)
    db.flush()
    if payload.samples:
        for s in payload.samples:
            db.add(
                TestSample(
                    test_run_id=run.id,
                    phase=SamplePhase(s.phase.value),
                    t_offset_ms=s.t_offset_ms,
                    value=s.value,
                    unit=s.unit,
                    meta=s.metadata,
                )
            )
    db.commit()
    loaded = get_test_run_eager(db, run.id)
    if loaded is None:
        raise RuntimeError("test run missing after commit")
    return loaded


def get_test_run_eager(db: Session, run_id: int) -> TestRun | None:
    stmt = select(TestRun).options(selectinload(TestRun.samples)).where(TestRun.id == run_id)
    return db.scalar(stmt)
