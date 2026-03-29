from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.schemas import SettingsOut, SettingsUpdate
from app.services.app_settings_service import (
    apply_settings_patch,
    get_app_settings,
    row_to_settings_out,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings_admin(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SettingsOut:
    row = get_app_settings(db, settings)
    return row_to_settings_out(row, settings)


@router.patch("", response_model=SettingsOut)
def patch_settings(
    body: SettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SettingsOut:
    row = get_app_settings(db, settings)
    try:
        apply_settings_patch(db, row, body)
        db.commit()
        db.refresh(row)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    return row_to_settings_out(row, settings)
