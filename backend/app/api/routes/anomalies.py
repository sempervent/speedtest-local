from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, select, true
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AnomalyEvent
from app.schemas import AnomalyEventOut, AnomalyListResponse, AnomalySummaryOut

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


def _anomaly_where(
    *,
    from_time: datetime | None,
    to_time: datetime | None,
    client_id: int | None,
    metric_name: str | None,
    severity: str | None,
):
    parts = []
    if from_time is not None:
        parts.append(AnomalyEvent.created_at >= from_time)
    if to_time is not None:
        parts.append(AnomalyEvent.created_at <= to_time)
    if client_id is not None:
        parts.append(AnomalyEvent.client_id == client_id)
    if metric_name:
        parts.append(AnomalyEvent.metric_name == metric_name)
    if severity:
        parts.append(AnomalyEvent.severity == severity)
    if not parts:
        return true()
    return and_(*parts)


@router.get("", response_model=AnomalyListResponse)
def list_anomalies(
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
    client_id: int | None = None,
    metric_name: str | None = None,
    severity: str | None = None,
) -> AnomalyListResponse:
    flt = _anomaly_where(
        from_time=from_time,
        to_time=to_time,
        client_id=client_id,
        metric_name=metric_name,
        severity=severity,
    )
    total = db.scalar(select(func.count()).select_from(AnomalyEvent).where(flt)) or 0
    offset = (page - 1) * page_size
    stmt = (
        select(AnomalyEvent).where(flt).order_by(desc(AnomalyEvent.created_at)).offset(offset).limit(page_size)
    )
    rows = db.scalars(stmt).all()
    return AnomalyListResponse(
        items=[AnomalyEventOut.model_validate(r) for r in rows],
        total=int(total),
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=AnomalySummaryOut)
def anomalies_summary(
    db: Annotated[Session, Depends(get_db)],
    since_days: Annotated[int, Query(ge=1, le=365)] = 14,
) -> AnomalySummaryOut:
    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    flt = AnomalyEvent.created_at >= since
    total = db.scalar(select(func.count()).select_from(AnomalyEvent).where(flt)) or 0

    by_metric: dict[str, int] = {}
    by_severity: dict[str, int] = {}

    m_stmt = (
        select(AnomalyEvent.metric_name, func.count())
        .where(flt)
        .group_by(AnomalyEvent.metric_name)
    )
    for name, cnt in db.execute(m_stmt).all():
        by_metric[str(name)] = int(cnt)

    s_stmt = (
        select(AnomalyEvent.severity, func.count())
        .where(flt)
        .group_by(AnomalyEvent.severity)
    )
    for sev, cnt in db.execute(s_stmt).all():
        by_severity[str(sev)] = int(cnt)

    return AnomalySummaryOut(
        total_recent=int(total),
        by_metric=by_metric,
        by_severity=by_severity,
    )
