"""e11 mandatory publication invariants

Revision ID: b8d1f64aa21c
Revises: 84bc0f49e2d1
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8d1f64aa21c"
down_revision: str | None = "84bc0f49e2d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE guild_config SET everyone_mention_enabled = TRUE "
            "WHERE everyone_mention_enabled IS FALSE"
        )
    )
    op.create_check_constraint(
        op.f("ck_guild_config_everyone_mention_required"),
        "guild_config",
        "everyone_mention_enabled",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_guild_config_everyone_mention_required"),
        "guild_config",
        type_="check",
    )
