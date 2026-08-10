"""e13 runtime observability heartbeats

Revision ID: 84bc0f49e2d1
Revises: 6fa5c9e77d20
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "84bc0f49e2d1"
down_revision: str | None = "6fa5c9e77d20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runtime_heartbeat",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("process_name", sa.String(length=32), nullable=False),
        sa.Column("instance_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["guild_id"],
            ["guild_config.guild_id"],
            name=op.f("fk_runtime_heartbeat_guild_id_guild_config"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_runtime_heartbeat")),
        sa.UniqueConstraint(
            "guild_id",
            "process_name",
            "instance_id",
            name="runtime_process_instance",
        ),
    )
    op.create_index(
        "ix_runtime_heartbeat_guild_process_seen",
        "runtime_heartbeat",
        ["guild_id", "process_name", "last_seen_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_runtime_heartbeat_guild_process_seen", table_name="runtime_heartbeat")
    op.drop_table("runtime_heartbeat")
