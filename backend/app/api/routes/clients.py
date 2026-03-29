from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client
from app.schemas import ClientListResponse, ClientOut

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=ClientListResponse)
def list_clients(
    db: Annotated[Session, Depends(get_db)],
    q: str | None = Query(default=None, description="Filter label contains"),
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> ClientListResponse:
    stmt = select(Client).order_by(Client.last_seen_at.desc()).limit(limit)
    if q:
        stmt = stmt.where(Client.label.ilike(f"%{q}%"))
    rows = db.scalars(stmt).all()
    total = db.scalar(select(func.count()).select_from(Client)) or 0
    return ClientListResponse(items=[ClientOut.model_validate(c) for c in rows], total=int(total))
