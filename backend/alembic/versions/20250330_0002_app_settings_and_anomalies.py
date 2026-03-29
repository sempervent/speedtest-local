"""app_settings singleton + anomaly_events

Revision ID: 0002
Revises: 0001
Create Date: 2025-03-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_label", sa.String(length=256), nullable=False),
        sa.Column("default_download_duration_seconds", sa.Float(), nullable=False),
        sa.Column("default_upload_duration_seconds", sa.Float(), nullable=False),
        sa.Column("default_parallel_streams", sa.Integer(), nullable=False),
        sa.Column("default_payload_size_bytes", sa.Integer(), nullable=False),
        sa.Column("default_ping_samples", sa.Integer(), nullable=False),
        sa.Column("default_warmup_ping_samples", sa.Integer(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.Column("allow_client_self_label", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_network_label", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("anomaly_baseline_runs", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("anomaly_deviation_percent", sa.Float(), nullable=False, server_default="25.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "anomaly_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("test_run_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("metric_name", sa.String(length=64), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("observed_value", sa.Float(), nullable=True),
        sa.Column("deviation_pct", sa.Float(), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["test_run_id"], ["test_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anomaly_events_created_at", "anomaly_events", ["created_at"], unique=False)
    op.create_index("ix_anomaly_events_test_run_id", "anomaly_events", ["test_run_id"], unique=False)
    op.create_index("ix_anomaly_events_client_id_created_at", "anomaly_events", ["client_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_anomaly_events_client_id_created_at", table_name="anomaly_events")
    op.drop_index("ix_anomaly_events_test_run_id", table_name="anomaly_events")
    op.drop_index("ix_anomaly_events_created_at", table_name="anomaly_events")
    op.drop_table("anomaly_events")
    op.drop_table("app_settings")
