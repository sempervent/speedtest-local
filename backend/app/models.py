import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


APP_SETTINGS_SINGLETON_ID = 1


class AppSettings(Base):
    """Single effective configuration row (id must always be 1)."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_label: Mapped[str] = mapped_column(String(256), nullable=False)
    default_download_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    default_upload_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    default_parallel_streams: Mapped[int] = mapped_column(Integer, nullable=False)
    default_payload_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    default_ping_samples: Mapped[int] = mapped_column(Integer, nullable=False)
    default_warmup_ping_samples: Mapped[int] = mapped_column(Integer, nullable=False)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allow_client_self_label: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    allow_network_label: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    anomaly_baseline_runs: Mapped[int] = mapped_column(Integer, nullable=False, server_default="20")
    anomaly_deviation_percent: Mapped[float] = mapped_column(Float, nullable=False, server_default="25.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"
    __table_args__ = (
        Index("ix_anomaly_events_created_at", "created_at"),
        Index("ix_anomaly_events_test_run_id", "test_run_id"),
        Index("ix_anomaly_events_client_id_created_at", "client_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    test_run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    deviation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    event_meta: Mapped[dict[str, Any]] = mapped_column("event_metadata", JSONB, server_default="{}")


class SamplePhase(str, enum.Enum):
    ping = "ping"
    download = "download"
    upload = "upload"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stable_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), unique=True, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(512), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(256), nullable=True)
    os: Mapped[str | None] = mapped_column(String(128), nullable=True)
    network_label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, server_default="{}")

    test_runs: Mapped[list["TestRun"]] = relationship("TestRun", back_populates="client")


class TestRun(Base):
    __tablename__ = "test_runs"
    __table_args__ = (
        Index("ix_test_runs_created_at", "created_at"),
        Index("ix_test_runs_client_id_created_at", "client_id", "created_at"),
        Index("ix_test_runs_network_label_created_at", "network_label", "created_at"),
        Index("ix_test_runs_server_label_created_at", "server_label", "created_at"),
        Index("ix_test_runs_success_created_at", "success", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    client_label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    server_label: Mapped[str] = mapped_column(String(256), nullable=False, server_default="default")
    latency_ms_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    jitter_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    download_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    upload_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    packet_loss_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    download_bytes_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_bytes_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    browser_user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    network_label: Mapped[str | None] = mapped_column(String(256), nullable=True)

    client: Mapped["Client | None"] = relationship("Client", back_populates="test_runs")
    samples: Mapped[list["TestSample"]] = relationship(
        "TestSample", back_populates="test_run", cascade="all, delete-orphan"
    )


class TestSample(Base):
    __tablename__ = "test_samples"
    __table_args__ = (Index("ix_test_samples_test_run_id", "test_run_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    phase: Mapped[SamplePhase] = mapped_column(Enum(SamplePhase, name="sample_phase"), nullable=False)
    t_offset_ms: Mapped[float] = mapped_column(Float, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, server_default="{}")

    test_run: Mapped["TestRun"] = relationship("TestRun", back_populates="samples")
