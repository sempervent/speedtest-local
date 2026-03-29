from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import StatsSummaryOut, TimeseriesPoint, TimeseriesResponse
from app.services.stats_service import Bucket, SummaryFilters, compute_summary, compute_timeseries

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary", response_model=StatsSummaryOut)
def stats_summary(
    db: Annotated[Session, Depends(get_db)],
    client_id: int | None = None,
    network_label: str | None = None,
    server_label: str | None = None,
    success: bool | None = None,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
) -> StatsSummaryOut:
    f = SummaryFilters(
        client_id=client_id,
        network_label=network_label,
        server_label=server_label,
        success=success,
        from_time=from_time,
        to_time=to_time,
    )
    data = compute_summary(db, f)
    return StatsSummaryOut(**data)


@router.get("/timeseries", response_model=TimeseriesResponse)
def stats_timeseries(
    db: Annotated[Session, Depends(get_db)],
    bucket: Bucket = "day",
    client_id: int | None = None,
    network_label: str | None = None,
    server_label: str | None = None,
    success: bool | None = None,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
) -> TimeseriesResponse:
    f = SummaryFilters(
        client_id=client_id,
        network_label=network_label,
        server_label=server_label,
        success=success,
        from_time=from_time,
        to_time=to_time,
    )
    points_raw = compute_timeseries(db, f, bucket)
    points = [TimeseriesPoint(**p) for p in points_raw]
    return TimeseriesResponse(bucket=bucket, points=points)
