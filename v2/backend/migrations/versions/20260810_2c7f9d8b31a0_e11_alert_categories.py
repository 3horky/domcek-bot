"""e11 configurable moderator alert categories

Revision ID: 2c7f9d8b31a0
Revises: c82175ef7904
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2c7f9d8b31a0"
down_revision: str | None = "c82175ef7904"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "guild_config",
        sa.Column(
            "alert_calendar_sync_enabled", sa.Boolean(), nullable=False, server_default="true"
        ),
    )
    op.add_column(
        "guild_config",
        sa.Column("alert_publication_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "guild_config",
        sa.Column(
            "alert_channel_operations_enabled", sa.Boolean(), nullable=False, server_default="true"
        ),
    )
    op.add_column(
        "guild_config",
        sa.Column(
            "alert_role_operations_enabled", sa.Boolean(), nullable=False, server_default="true"
        ),
    )
    op.add_column(
        "guild_config",
        sa.Column(
            "alert_publication_reminder_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("guild_config", "alert_publication_reminder_enabled")
    op.drop_column("guild_config", "alert_role_operations_enabled")
    op.drop_column("guild_config", "alert_channel_operations_enabled")
    op.drop_column("guild_config", "alert_publication_enabled")
    op.drop_column("guild_config", "alert_calendar_sync_enabled")
