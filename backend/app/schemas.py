from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SamplePhaseSchema(str, Enum):
    ping = "ping"
    download = "download"
    upload = "upload"


class TestSampleCreate(BaseModel):
    phase: SamplePhaseSchema
    t_offset_ms: float = Field(ge=0)
    value: float
    unit: str = Field(max_length=32)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TestRunCreate(BaseModel):
    started_at: datetime | None = None
    completed_at: datetime | None = None
    client_stable_id: UUID | None = None
    client_label: str | None = Field(default=None, max_length=256)
    server_label: str | None = Field(default=None, max_length=256)
    network_label: str | None = Field(default=None, max_length=256)
    latency_ms_avg: float | None = None
    jitter_ms: float | None = None
    download_mbps: float | None = None
    upload_mbps: float | None = None
    packet_loss_pct: float | None = Field(default=None, ge=0, le=100)
    download_bytes_total: int | None = Field(default=None, ge=0)
    upload_bytes_total: int | None = Field(default=None, ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)
    success: bool = True
    failure_reason: str | None = None
    raw_metrics_json: dict[str, Any] | None = None
    browser_user_agent: str | None = None
    notes: str | None = None
    samples: list[TestSampleCreate] | None = None


class TestSampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    phase: str
    t_offset_ms: float
    value: float
    unit: str
    metadata: dict[str, Any] = Field(alias="meta")


class TestRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    client_id: int | None
    client_label: str | None
    server_label: str
    latency_ms_avg: float | None
    jitter_ms: float | None
    download_mbps: float | None
    upload_mbps: float | None
    packet_loss_pct: float | None
    download_bytes_total: int | None
    upload_bytes_total: int | None
    duration_seconds: float | None
    success: bool
    failure_reason: str | None
    raw_metrics_json: dict[str, Any] | None
    browser_user_agent: str | None
    ip_address: str | None
    notes: str | None
    network_label: str | None
    samples: list[TestSampleOut] = Field(default_factory=list)


class TestRunSummaryOut(BaseModel):
    """List row without per-sample payload."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    client_id: int | None
    client_label: str | None
    server_label: str
    latency_ms_avg: float | None
    jitter_ms: float | None
    download_mbps: float | None
    upload_mbps: float | None
    packet_loss_pct: float | None
    download_bytes_total: int | None
    upload_bytes_total: int | None
    duration_seconds: float | None
    success: bool
    failure_reason: str | None
    browser_user_agent: str | None
    ip_address: str | None
    notes: str | None
    network_label: str | None


class TestRunListResponse(BaseModel):
    items: list[TestRunSummaryOut]
    total: int
    page: int
    page_size: int


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    stable_id: UUID | None
    first_seen_at: datetime
    last_seen_at: datetime
    label: str | None
    hostname: str | None
    device_type: str | None
    browser: str | None
    os: str | None
    network_label: str | None
    metadata: dict[str, Any] = Field(alias="meta")


class ClientListResponse(BaseModel):
    items: list[ClientOut]
    total: int


class AppConfigOut(BaseModel):
    server_label: str
    defaults: dict[str, Any]
    download_max_bytes: int
    upload_max_bytes: int
    allow_client_self_label: bool = True
    allow_network_label: bool = True


class PingResponse(BaseModel):
    """Server echo for RTT measurement. Client computes latency from request start to response."""

    server_ts_ms: float


class UploadResponse(BaseModel):
    bytes_received: int


class StatsSummaryOut(BaseModel):
    count: int
    download_mbps_avg: float | None
    download_mbps_p50: float | None
    download_mbps_p95: float | None
    upload_mbps_avg: float | None
    upload_mbps_p50: float | None
    upload_mbps_p95: float | None
    latency_ms_avg: float | None
    jitter_ms_avg: float | None


class TimeseriesPoint(BaseModel):
    bucket_start: datetime
    download_mbps_avg: float | None
    upload_mbps_avg: float | None
    latency_ms_avg: float | None
    jitter_ms_avg: float | None
    run_count: int


class TimeseriesResponse(BaseModel):
    bucket: str
    points: list[TimeseriesPoint]


class SettingsUpdate(BaseModel):
    server_label: str | None = Field(default=None, max_length=256)
    default_download_duration_sec: float | None = Field(default=None, gt=0, le=600)
    default_upload_duration_sec: float | None = Field(default=None, gt=0, le=600)
    default_parallel_streams: int | None = Field(default=None, ge=1, le=32)
    default_payload_bytes: int | None = Field(default=None, ge=1024)
    default_ping_samples: int | None = Field(default=None, ge=5, le=500)
    default_warmup_ping_samples: int | None = Field(default=None, ge=0, le=100)
    retention_days: int | None = Field(
        default=None,
        description="Null disables age-based retention hints until set.",
    )
    retention_days_placeholder: int | None = Field(
        default=None,
        ge=1,
        le=3650,
        description="Deprecated; prefer retention_days.",
    )
    allow_client_self_label: bool | None = None
    allow_network_label: bool | None = None
    anomaly_baseline_runs: int | None = Field(default=None, ge=3, le=500)
    anomaly_deviation_percent: float | None = Field(default=None, gt=0, le=200)

    @field_validator("retention_days")
    @classmethod
    def retention_range(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 3650):
            raise ValueError("retention_days must be 1..3650 or null")
        return v

    @field_validator("default_payload_bytes")
    @classmethod
    def cap_payload(cls, v: int | None) -> int | None:
        if v is not None and v > 128 * 1024 * 1024:
            raise ValueError("default_payload_bytes too large (max 128 MiB for UI hint)")
        return v


class SettingsOut(BaseModel):
    """Persisted app_settings plus env-scoped byte caps."""

    server_label: str
    default_download_duration_sec: float
    default_upload_duration_sec: float
    default_parallel_streams: int
    default_payload_bytes: int
    default_ping_samples: int
    default_warmup_ping_samples: int
    retention_days: int | None
    allow_client_self_label: bool
    allow_network_label: bool
    anomaly_baseline_runs: int
    anomaly_deviation_percent: float
    download_max_bytes: int
    upload_max_bytes: int


class PruneRequest(BaseModel):
    dry_run: bool = True
    retention_days: int | None = Field(
        default=None,
        ge=1,
        le=3650,
        description="Defaults to app_settings.retention_days when omitted.",
    )


class PruneResult(BaseModel):
    dry_run: bool
    retention_days_used: int
    cutoff: datetime
    test_runs_matched: int
    test_samples_deleted: int
    test_runs_deleted: int


class AnomalyEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    created_at: datetime
    test_run_id: int
    client_id: int | None
    metric_name: str
    baseline_value: float | None
    observed_value: float | None
    deviation_pct: float | None
    severity: str
    metadata: dict[str, Any] = Field(validation_alias="event_meta", serialization_alias="metadata")


class AnomalyListResponse(BaseModel):
    items: list[AnomalyEventOut]
    total: int
    page: int
    page_size: int


class AnomalySummaryOut(BaseModel):
    total_recent: int
    by_metric: dict[str, int]
    by_severity: dict[str, int]


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
