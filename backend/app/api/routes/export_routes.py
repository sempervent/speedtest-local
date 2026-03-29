"""Stable export paths under /api/export/ (chunked streaming)."""

import csv
import json
from datetime import datetime
from io import StringIO
from typing import Annotated, Iterator

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.api.routes.tests import _apply_filters
from app.database import get_db
from app.models import TestRun
from app.schemas import TestRunSummaryOut

router = APIRouter(prefix="/api/export", tags=["export"])


def _filtered_runs_stmt(
    *,
    from_time: datetime | None,
    to_time: datetime | None,
    client_id: int | None,
    network_label: str | None,
    server_label: str | None,
    success: bool | None,
    limit: int,
):
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
    return base.order_by(desc(TestRun.created_at)).limit(limit)


@router.get("/tests.json")
def export_tests_json(
    db: Annotated[Session, Depends(get_db)],
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    client_id: int | None = None,
    network_label: str | None = None,
    server_label: str | None = None,
    success: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=50_000)] = 10_000,
) -> StreamingResponse:
    stmt = _filtered_runs_stmt(
        from_time=from_time,
        to_time=to_time,
        client_id=client_id,
        network_label=network_label,
        server_label=server_label,
        success=success,
        limit=limit,
    )
    rows = list(db.scalars(stmt).all())

    def gen() -> Iterator[bytes]:
        yield b"["
        first = True
        for r in rows:
            if not first:
                yield b","
            first = False
            payload = TestRunSummaryOut.model_validate(r).model_dump(mode="json")
            yield json.dumps(payload, default=str).encode()
        yield b"]"

    return StreamingResponse(
        gen(),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="test_runs.json"'},
    )


@router.get("/tests.csv")
def export_tests_csv(
    db: Annotated[Session, Depends(get_db)],
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    client_id: int | None = None,
    network_label: str | None = None,
    server_label: str | None = None,
    success: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=50_000)] = 10_000,
) -> StreamingResponse:
    stmt = _filtered_runs_stmt(
        from_time=from_time,
        to_time=to_time,
        client_id=client_id,
        network_label=network_label,
        server_label=server_label,
        success=success,
        limit=limit,
    )
    rows = list(db.scalars(stmt).all())

    header = [
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

    def gen() -> Iterator[bytes]:
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(header)
        yield buf.getvalue().encode()
        buf.seek(0)
        buf.truncate(0)
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
            yield buf.getvalue().encode()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        gen(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="test_runs.csv"'},
    )
