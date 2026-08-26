"""Initial schema - users, cases, devices, artifacts, audit_log

Revision ID: 001
Revises:
Create Date: 2026-08-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    user_role_enum = ENUM("admin", "investigator", "viewer", name="userrole", create_type=False)
    user_role_enum.create(op.get_bind(), checkfirst=True)

    case_status_enum = ENUM("open", "in_progress", "closed", name="casestatus", create_type=False)
    case_status_enum.create(op.get_bind(), checkfirst=True)

    artifact_status_enum = ENUM("queued", "parsing", "parsed", "parse_failed", name="artifactstatus", create_type=False)
    artifact_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "cases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", case_status_enum, nullable=False, server_default="open"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "case_investigators",
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_type", sa.String(50), nullable=False),
        sa.Column("os", sa.String(100), nullable=True),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "raw_artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False, index=True),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("status", artifact_status_enum, nullable=False, server_default="queued"),
        sa.Column("status_reason", sa.Text, nullable=True),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=False),
        sa.Column("target_id", sa.String(255), nullable=True),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("raw_artifacts")
    op.drop_table("devices")
    op.drop_table("case_investigators")
    op.drop_table("cases")
    op.drop_table("users")
    ENUM(name="artifactstatus").drop(op.get_bind(), checkfirst=True)
    ENUM(name="casestatus").drop(op.get_bind(), checkfirst=True)
    ENUM(name="userrole").drop(op.get_bind(), checkfirst=True)
