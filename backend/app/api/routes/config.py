from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.schemas import AppConfigOut
from app.services.app_settings_service import effective_config_dict, get_app_settings

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config", response_model=AppConfigOut)
def get_public_config(
    db: Annotated[Session, Depends(get_db)],
    settings: Settings = Depends(get_settings),
) -> AppConfigOut:
    row = get_app_settings(db, settings)
    merged = effective_config_dict(row)
    return AppConfigOut(
        server_label=str(merged["server_label"]),
        defaults={
            "download_duration_sec": merged["default_download_duration_sec"],
            "upload_duration_sec": merged["default_upload_duration_sec"],
            "parallel_streams": merged["default_parallel_streams"],
            "payload_bytes": merged["default_payload_bytes"],
            "ping_samples": merged["default_ping_samples"],
            "warmup_ping_samples": merged["default_warmup_ping_samples"],
        },
        download_max_bytes=settings.download_max_bytes,
        upload_max_bytes=settings.upload_max_bytes,
        allow_client_self_label=row.allow_client_self_label,
        allow_network_label=row.allow_network_label,
    )
