"""e11 recoverable channel archiving

Revision ID: d7a4cb1268ef
Revises: c3e72a19d640
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7a4cb1268ef"
down_revision: str | None = "c3e72a19d640"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_channel_archive_request_state"),
        "channel_archive_request",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_channel_archive_request_state"),
        "channel_archive_request",
        "state IN ('pending', 'archiving', 'approved', 'rejected', "
        "'expired', 'executed', 'failed')",
    )
    op.drop_index(
        "uq_channel_archive_request_pending_channel",
        table_name="channel_archive_request",
    )
    op.create_index(
        "uq_channel_archive_request_pending_channel",
        "channel_archive_request",
        ["guild_id", "discord_channel_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('pending', 'archiving')"),
    )


def downgrade() -> None:
    op.execute("UPDATE channel_archive_request SET state = 'failed' WHERE state = 'archiving'")
    op.drop_index(
        "uq_channel_archive_request_pending_channel",
        table_name="channel_archive_request",
    )
    op.create_index(
        "uq_channel_archive_request_pending_channel",
        "channel_archive_request",
        ["guild_id", "discord_channel_id"],
        unique=True,
        postgresql_where=sa.text("state = 'pending'"),
    )
    op.drop_constraint(
        op.f("ck_channel_archive_request_state"),
        "channel_archive_request",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_channel_archive_request_state"),
        "channel_archive_request",
        "state IN ('pending', 'approved', 'rejected', 'expired', 'executed', 'failed')",
    )
