"""e8 integration task results

Revision ID: a93bd44a10e8
Revises: 57cd18009c0b
Create Date: 2026-08-09 22:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a93bd44a10e8"
down_revision: str | None = "57cd18009c0b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "integration_task",
        sa.Column(
            "result_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("integration_task", "result_value")
