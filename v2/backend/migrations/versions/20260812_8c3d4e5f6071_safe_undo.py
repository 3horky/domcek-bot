"""Add durable state-safe undo operations.

Revision ID: 8c3d4e5f6071
Revises: 7b2c3d4e5f60
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8c3d4e5f6071"
down_revision: str | None = "7b2c3d4e5f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "undo_operation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("operation_type", sa.String(length=32), nullable=False),
        sa.Column("object_id", sa.String(length=160), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=False),
        sa.Column("before_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("after_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False, server_default="available"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("undone_at", sa.DateTime(timezone=True)),
        sa.Column("undone_by_user_id", sa.BigInteger()),
        sa.Column("last_block_reason", sa.String(length=100)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "operation_type IN ('role_change', 'channel_create', 'channel_archive')",
            name=op.f("ck_undo_operation_operation_type"),
        ),
        sa.CheckConstraint(
            "state IN ('available', 'undoing', 'undone')",
            name=op.f("ck_undo_operation_state"),
        ),
        sa.ForeignKeyConstraint(
            ["guild_id"],
            ["guild_config.guild_id"],
            name=op.f("fk_undo_operation_guild_id_guild_config"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_undo_operation")),
    )
    op.create_index(
        "ix_undo_operation_guild_state_created",
        "undo_operation",
        ["guild_id", "state", "created_at"],
    )
    op.add_column("channel_archive_request", sa.Column("restore_snapshot", postgresql.JSONB()))
    op.add_column("channel_archive_request", sa.Column("archived_snapshot", postgresql.JSONB()))
    op.add_column("channel_archive_request", sa.Column("undo_id", postgresql.UUID(as_uuid=True)))


def downgrade() -> None:
    op.drop_column("channel_archive_request", "undo_id")
    op.drop_column("channel_archive_request", "archived_snapshot")
    op.drop_column("channel_archive_request", "restore_snapshot")
    op.drop_index("ix_undo_operation_guild_state_created", table_name="undo_operation")
    op.drop_table("undo_operation")
