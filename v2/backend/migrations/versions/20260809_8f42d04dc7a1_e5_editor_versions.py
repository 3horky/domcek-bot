"""e5 editor versions

Revision ID: 8f42d04dc7a1
Revises: e219fe464c61
Create Date: 2026-08-09 15:25:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8f42d04dc7a1"
down_revision: str | None = "e219fe464c61"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "manual_event",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_manual_event_positive_version"),
        "manual_event",
        "version >= 1",
    )
    op.add_column(
        "info_announcement",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_info_announcement_positive_version"),
        "info_announcement",
        "version >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_info_announcement_positive_version"),
        "info_announcement",
        type_="check",
    )
    op.drop_column("info_announcement", "version")
    op.drop_constraint(
        op.f("ck_manual_event_positive_version"),
        "manual_event",
        type_="check",
    )
    op.drop_column("manual_event", "version")
