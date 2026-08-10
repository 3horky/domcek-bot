"""e9 settings optimistic versions

Revision ID: c82175ef7904
Revises: a93bd44a10e8
Create Date: 2026-08-10 00:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c82175ef7904"
down_revision: str | None = "a93bd44a10e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("guild_config", "calendar_source", "reaction_config"):
        op.add_column(table, sa.Column("version", sa.Integer(), server_default="1", nullable=False))
        op.create_check_constraint(op.f(f"ck_{table}_positive_version"), table, "version >= 1")


def downgrade() -> None:
    for table in ("reaction_config", "calendar_source", "guild_config"):
        op.drop_constraint(op.f(f"ck_{table}_positive_version"), table, type_="check")
        op.drop_column(table, "version")
