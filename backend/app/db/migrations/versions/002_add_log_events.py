"""Add log_events table

Revision ID: 002
Revises: 001
Create Date: 2026-08-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "log_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("artifact_id", UUID(as_uuid=True), sa.ForeignKey("raw_artifacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_type", sa.String(100), nullable=False),
        sa.Column("actor", sa.String(500), nullable=True),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("object", sa.String(1000), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column("raw_line", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_log_events_case_id", "log_events", ["case_id"])
    op.create_index("ix_log_events_device_id", "log_events", ["device_id"])
    op.create_index("ix_log_events_timestamp", "log_events", ["timestamp"])
    op.create_index("ix_log_events_ip_address", "log_events", ["ip_address"])
    op.create_index("ix_log_events_file_hash", "log_events", ["file_hash"])
    op.create_index("ix_log_events_source_type", "log_events", ["source_type"])
    op.create_index("ix_log_events_action", "log_events", ["action"])


def downgrade() -> None:
    op.drop_table("log_events")
