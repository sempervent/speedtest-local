"""Durable singleton app_settings. Env `Settings` seeds the row once; DB is source of truth after."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import APP_SETTINGS_SINGLETON_ID, AppSettings
from app.schemas import SettingsOut, SettingsUpdate


def _defaults_from_env(env: Settings) -> dict:
    return {
        "id": APP_SETTINGS_SINGLETON_ID,
        "server_label": env.server_label,
        "default_download_duration_seconds": float(env.default_download_duration_sec),
        "default_upload_duration_seconds": float(env.default_upload_duration_sec),
        "default_parallel_streams": int(env.default_parallel_streams),
        "default_payload_size_bytes": int(env.default_payload_bytes),
        "default_ping_samples": int(env.default_ping_samples),
        "default_warmup_ping_samples": int(env.default_warmup_ping_samples),
        # Null until operator sets retention via API (env no longer forces a policy).
        "retention_days": None,
        "allow_client_self_label": True,
        "allow_network_label": True,
        "anomaly_baseline_runs": 20,
        "anomaly_deviation_percent": 25.0,
    }


def ensure_app_settings_row(db: Session, env: Settings) -> AppSettings:
    row = db.get(AppSettings, APP_SETTINGS_SINGLETON_ID)
    if row is not None:
        return row
    row = AppSettings(**_defaults_from_env(env))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_app_settings(db: Session, env: Settings) -> AppSettings:
    """Return singleton row, creating it from env if missing."""
    return ensure_app_settings_row(db, env)


def row_to_settings_out(row: AppSettings, env: Settings) -> SettingsOut:
    return SettingsOut(
        server_label=row.server_label,
        default_download_duration_sec=row.default_download_duration_seconds,
        default_upload_duration_sec=row.default_upload_duration_seconds,
        default_parallel_streams=row.default_parallel_streams,
        default_payload_bytes=row.default_payload_size_bytes,
        default_ping_samples=row.default_ping_samples,
        default_warmup_ping_samples=row.default_warmup_ping_samples,
        retention_days=row.retention_days,
        allow_client_self_label=row.allow_client_self_label,
        allow_network_label=row.allow_network_label,
        anomaly_baseline_runs=row.anomaly_baseline_runs,
        anomaly_deviation_percent=row.anomaly_deviation_percent,
        download_max_bytes=env.download_max_bytes,
        upload_max_bytes=env.upload_max_bytes,
    )


def apply_settings_patch(db: Session, row: AppSettings, patch: SettingsUpdate) -> AppSettings:
    fs = patch.model_fields_set
    if "server_label" in fs:
        if patch.server_label is None:
            raise ValueError("server_label cannot be null")
        row.server_label = patch.server_label
    if "default_download_duration_sec" in fs:
        row.default_download_duration_seconds = float(patch.default_download_duration_sec)  # type: ignore[arg-type]
    if "default_upload_duration_sec" in fs:
        row.default_upload_duration_seconds = float(patch.default_upload_duration_sec)  # type: ignore[arg-type]
    if "default_parallel_streams" in fs:
        row.default_parallel_streams = int(patch.default_parallel_streams)  # type: ignore[arg-type]
    if "default_payload_bytes" in fs:
        row.default_payload_size_bytes = int(patch.default_payload_bytes)  # type: ignore[arg-type]
    if "default_ping_samples" in fs:
        row.default_ping_samples = int(patch.default_ping_samples)  # type: ignore[arg-type]
    if "default_warmup_ping_samples" in fs:
        row.default_warmup_ping_samples = int(patch.default_warmup_ping_samples)  # type: ignore[arg-type]
    if "retention_days" in fs:
        row.retention_days = patch.retention_days
    # backward compatibility with older UI
    if "retention_days_placeholder" in fs and "retention_days" not in fs:
        v = patch.retention_days_placeholder
        row.retention_days = int(v) if v is not None else None
    if "allow_client_self_label" in fs:
        row.allow_client_self_label = bool(patch.allow_client_self_label)
    if "allow_network_label" in fs:
        row.allow_network_label = bool(patch.allow_network_label)
    if "anomaly_baseline_runs" in fs:
        row.anomaly_baseline_runs = int(patch.anomaly_baseline_runs)  # type: ignore[arg-type]
    if "anomaly_deviation_percent" in fs:
        row.anomaly_deviation_percent = float(patch.anomaly_deviation_percent)  # type: ignore[arg-type]

    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    db.flush()
    return row


def effective_config_dict(row: AppSettings) -> dict:
    """Shape aligned with public /api/config defaults."""
    return {
        "server_label": row.server_label,
        "default_download_duration_sec": row.default_download_duration_seconds,
        "default_upload_duration_sec": row.default_upload_duration_seconds,
        "default_parallel_streams": row.default_parallel_streams,
        "default_payload_bytes": row.default_payload_size_bytes,
        "default_ping_samples": row.default_ping_samples,
        "default_warmup_ping_samples": row.default_warmup_ping_samples,
    }


def load_row_for_readonly(db: Session) -> AppSettings | None:
    return db.scalar(select(AppSettings).where(AppSettings.id == APP_SETTINGS_SINGLETON_ID))
