"""Persist the exact seen reaction in the publication snapshot.

Revision ID: 4a1b2c3d4e5f
Revises: e4c28f5619ad
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4a1b2c3d4e5f"
down_revision: str | None = "e4c28f5619ad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("publication_message", sa.Column("reaction_emoji", sa.String(200)))
    op.execute(
        "UPDATE publication_message SET reaction_emoji = '✅' "
        "WHERE seen_target IS TRUE AND reaction_emoji IS NULL"
    )


def downgrade() -> None:
    op.drop_column("publication_message", "reaction_emoji")
