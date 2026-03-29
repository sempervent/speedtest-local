import csv
import io
import json
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.database import get_db
from app.models import TestRun
from app.schemas import (
    TestRunCreate,
    TestRunListResponse,
    TestRunOut,
    TestRunSummaryOut,
)
from app.services.anomaly_service import record_anomalies_for_run
from app.services.app_settings_service import get_app_settings
from app.services.test_run_service import create_test_run, get_test_run_eager

router = APIRouter(prefix="/api/tests", tags=["tests"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _apply_filters(
    stmt,
    *,
    from_time: datetime | None,
    to_time: datetime | None,
    client_id: int | None,
    network_label: str | None,
    server_label: str | None,
    success: bool | None,
):
    if from_time is not None:
        stmt = stmt.where(TestRun.created_at >= from_time)
    if to_time is not None:
        stmt = stmt.where(TestRun.created_at <= to_time)
    if client_id is not None:
        stmt = stmt.where(TestRun.client_id == client_id)
    if network_label:
        stmt = stmt.where(TestRun.network_label == network_label)
    if server_label:
        stmt = stmt.where(TestRun.server_label == server_label)
    if success is not None:
        stmt = stmt.where(TestRun.success == success)
    return stmt


@router.post("", response_model=TestRunOut)
def post_test(
    body: TestRunCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TestRunOut:
    app_row = get_app_settings(db, settings)
    adj = body.model_copy(deep=True)
    if not app_row.allow_client_self_label:
        adj.client_label = None
    if not app_row.allow_network_label:
        adj.network_label = None
    run = create_test_run(
        db,
        adj,
        app_settings=app_row,
        env_settings=settings,
        ip_address=_client_ip(request),
    )
    record_anomalies_for_run(db, run, app_row)
    db.commit()
    loaded = get_test_run_eager(db, run.id)
    if loaded is None:
        raise HTTPException(status_code=500, detail="failed to persist test run")
    return TestRunOut.model_validate(loaded)


@router.get("", response_model=TestRunListResponse)
def list_tests(
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    client_id: int | None = None,
    network_label: str | None = None,
    server_label: str | None = None,
    success: bool | None = None,
    sort: Literal["created_at", "download_mbps", "upload_mbps", "latency_ms_avg"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
) -> TestRunListResponse:
    count_stmt = select(func.count()).select_from(TestRun)
    count_stmt = _apply_filters(
        count_stmt,
        from_time=from_time,
        to_time=to_time,
        client_id=client_id,
        network_label=network_label,
        server_label=server_label,
        success=success,
    )
    total = db.scalar(count_stmt) or 0

    base = select(TestRun)
    base = _apply_filters(
        base,
        from_time=from_time,
        to_time=to_time,
        client_id=client_id,
        network_label=network_label,
        server_label=server_label,
        success=success,
    )
    sort_col = getattr(TestRun, sort)
    base = base.order_by(desc(sort_col) if order == "desc" else asc(sort_col))
    offset = (page - 1) * page_size
    rows = db.scalars(base.offset(offset).limit(page_size)).all()
    items = [TestRunSummaryOut.model_validate(r) for r in rows]
    return TestRunListResponse(items=items, total=int(total), page=page, page_size=page_size)


@router.get("/export")
def export_tests(
    db: Annotated[Session, Depends(get_db)],
    export_format: Annotated[Literal["json", "csv"], Query(alias="format")] = "json",
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    client_id: int | None = None,
    network_label: str | None = None,
    server_label: str | None = None,
    success: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=10_000)] = 5000,
) -> Response:
    base = select(TestRun)
    base = _apply_filters(
        base,
        from_time=from_time,
        to_time=to_time,
        client_id=client_id,
        network_label=network_label,
        server_label=server_label,
        success=success,
    )
    base = base.order_by(desc(TestRun.created_at)).limit(limit)
    rows = db.scalars(base).all()
    if export_format == "json":
        payload = [TestRunSummaryOut.model_validate(r).model_dump(mode="json") for r in rows]
        return Response(
            content=json.dumps(payload, default=str),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="test_runs.json"'},
        )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "id",
            "created_at",
            "client_id",
            "client_label",
            "network_label",
            "server_label",
            "download_mbps",
            "upload_mbps",
            "latency_ms_avg",
            "jitter_ms",
            "success",
        ]
    )
    for r in rows:
        w.writerow(
            [
                r.id,
                r.created_at.isoformat() if r.created_at else "",
                r.client_id or "",
                r.client_label or "",
                r.network_label or "",
                r.server_label,
                r.download_mbps or "",
                r.upload_mbps or "",
                r.latency_ms_avg or "",
                r.jitter_ms or "",
                r.success,
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="test_runs.csv"'},
    )


@router.get("/{test_id}", response_model=TestRunOut)
def get_test(
    test_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> TestRunOut:
    run = db.scalar(
        select(TestRun).options(selectinload(TestRun.samples)).where(TestRun.id == test_id)
    )
    if run is None:
        raise HTTPException(status_code=404, detail="test run not found")
    return TestRunOut.model_validate(run)
