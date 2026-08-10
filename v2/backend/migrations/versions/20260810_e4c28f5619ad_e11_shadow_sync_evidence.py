"""e11 trustworthy shadow calendar sync evidence

Revision ID: e4c28f5619ad
Revises: d7a4cb1268ef
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e4c28f5619ad"
down_revision: str | None = "d7a4cb1268ef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "shadow_publication",
        sa.Column(
            "calendar_sync_valid",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "shadow_publication",
        sa.Column(
            "calendar_sync_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("shadow_publication", "calendar_sync_valid", server_default=None)
    op.alter_column("shadow_publication", "calendar_sync_evidence", server_default=None)


def downgrade() -> None:
    op.drop_column("shadow_publication", "calendar_sync_evidence")
    op.drop_column("shadow_publication", "calendar_sync_valid")
