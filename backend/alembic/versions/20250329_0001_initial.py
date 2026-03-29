"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-03-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

sample_phase = postgresql.ENUM("ping", "download", "upload", name="sample_phase")


def upgrade() -> None:
    sample_phase.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stable_id", sa.Uuid(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=True),
        sa.Column("hostname", sa.String(length=512), nullable=True),
        sa.Column("device_type", sa.String(length=128), nullable=True),
        sa.Column("browser", sa.String(length=256), nullable=True),
        sa.Column("os", sa.String(length=128), nullable=True),
        sa.Column("network_label", sa.String(length=256), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stable_id"),
    )
    op.create_table(
        "test_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("client_label", sa.String(length=256), nullable=True),
        sa.Column("server_label", sa.String(length=256), server_default="default", nullable=False),
        sa.Column("latency_ms_avg", sa.Float(), nullable=True),
        sa.Column("jitter_ms", sa.Float(), nullable=True),
        sa.Column("download_mbps", sa.Float(), nullable=True),
        sa.Column("upload_mbps", sa.Float(), nullable=True),
        sa.Column("packet_loss_pct", sa.Float(), nullable=True),
        sa.Column("download_bytes_total", sa.Integer(), nullable=True),
        sa.Column("upload_bytes_total", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("raw_metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("browser_user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("network_label", sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_runs_created_at", "test_runs", ["created_at"], unique=False)
    op.create_index("ix_test_runs_client_id_created_at", "test_runs", ["client_id", "created_at"], unique=False)
    op.create_index("ix_test_runs_network_label_created_at", "test_runs", ["network_label", "created_at"], unique=False)
    op.create_index("ix_test_runs_server_label_created_at", "test_runs", ["server_label", "created_at"], unique=False)
    op.create_index("ix_test_runs_success_created_at", "test_runs", ["success", "created_at"], unique=False)
    op.create_table(
        "test_samples",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("test_run_id", sa.Integer(), nullable=False),
        sa.Column("phase", postgresql.ENUM("ping", "download", "upload", name="sample_phase", create_type=False), nullable=False),
        sa.Column("t_offset_ms", sa.Float(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["test_run_id"], ["test_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_samples_test_run_id", "test_samples", ["test_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_test_samples_test_run_id", table_name="test_samples")
    op.drop_table("test_samples")
    op.drop_index("ix_test_runs_success_created_at", table_name="test_runs")
    op.drop_index("ix_test_runs_server_label_created_at", table_name="test_runs")
    op.drop_index("ix_test_runs_network_label_created_at", table_name="test_runs")
    op.drop_index("ix_test_runs_client_id_created_at", table_name="test_runs")
    op.drop_index("ix_test_runs_created_at", table_name="test_runs")
    op.drop_table("test_runs")
    op.drop_table("clients")
    sample_phase.drop(op.get_bind(), checkfirst=True)
