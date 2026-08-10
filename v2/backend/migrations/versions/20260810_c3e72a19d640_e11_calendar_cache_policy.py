"""e11 explicit calendar cache fallback policy

Revision ID: c3e72a19d640
Revises: b8d1f64aa21c
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3e72a19d640"
down_revision: str | None = "b8d1f64aa21c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "guild_config",
        sa.Column(
            "allow_stale_calendar_cache",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.alter_column("guild_config", "allow_stale_calendar_cache", server_default=None)


def downgrade() -> None:
    op.drop_column("guild_config", "allow_stale_calendar_cache")
