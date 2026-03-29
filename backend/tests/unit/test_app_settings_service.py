"""Pure tests for settings patch field mapping."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.schemas import SettingsUpdate
from app.services.app_settings_service import apply_settings_patch


def test_apply_settings_patch_updates_anomaly_fields():
    row = SimpleNamespace(
        server_label="s",
        default_download_duration_seconds=10.0,
        default_upload_duration_seconds=10.0,
        default_parallel_streams=4,
        default_payload_size_bytes=16_777_216,
        default_ping_samples=30,
        default_warmup_ping_samples=5,
        retention_days=None,
        allow_client_self_label=True,
        allow_network_label=True,
        anomaly_baseline_runs=20,
        anomaly_deviation_percent=25.0,
        updated_at=None,
    )
    db = MagicMock()
    patch = SettingsUpdate(anomaly_baseline_runs=10, anomaly_deviation_percent=15.0)
    apply_settings_patch(db, row, patch)  # type: ignore[arg-type]
    assert row.anomaly_baseline_runs == 10
    assert row.anomaly_deviation_percent == 15.0
    db.add.assert_called_once_with(row)
    db.flush.assert_called_once()
