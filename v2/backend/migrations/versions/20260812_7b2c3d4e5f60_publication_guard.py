"""Add durable publication guard state and settings.

Revision ID: 7b2c3d4e5f60
Revises: 4a1b2c3d4e5f
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7b2c3d4e5f60"
down_revision: str | None = "4a1b2c3d4e5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "guild_config",
        sa.Column(
            "publication_grace_seconds", sa.SmallInteger(), nullable=False, server_default="30"
        ),
    )
    op.add_column(
        "guild_config",
        sa.Column(
            "publication_guard_recipient_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_check_constraint(
        "ck_guild_config_publication_grace_seconds",
        "guild_config",
        "publication_grace_seconds BETWEEN 0 AND 300",
    )
    op.add_column("publication_run", sa.Column("release_at", sa.DateTime(timezone=True)))
    op.add_column("publication_run", sa.Column("decision_at", sa.DateTime(timezone=True)))
    op.add_column("publication_run", sa.Column("decision_by_user_id", sa.BigInteger()))
    op.add_column("publication_run", sa.Column("decision_reason", sa.String(length=64)))
    op.execute("ALTER TABLE publication_run DROP CONSTRAINT IF EXISTS ck_publication_run_state")
    op.execute(
        "ALTER TABLE publication_run DROP CONSTRAINT IF EXISTS "
        "ck_publication_run_ck_publication_run_state"
    )
    op.execute(
        "ALTER TABLE publication_run ADD CONSTRAINT ck_publication_run_state CHECK ("
        "state IN ('preparing', 'waiting_for_release', 'publishing', "
        "'succeeded_automatic', 'succeeded_manual', 'skipped_after_manual', "
        "'failed', 'retry_pending', 'partially_published', 'cancelled'))"
    )
    op.create_index(
        "ix_publication_run_guard_release",
        "publication_run",
        ["state", "release_at"],
        unique=False,
    )
    op.create_table(
        "publication_guard_notice",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("publication_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_user_id", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("nonce", sa.String(length=64), nullable=False),
        sa.Column("discord_channel_id", sa.BigInteger()),
        sa.Column("discord_message_id", sa.BigInteger()),
        sa.Column("error_detail", sa.Text()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "state IN ('pending', 'sent', 'failed', 'deleted')",
            name=op.f("ck_publication_guard_notice_state"),
        ),
        sa.ForeignKeyConstraint(
            ["publication_run_id"],
            ["publication_run.id"],
            name=op.f("fk_publication_guard_notice_publication_run_id_publication_run"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_publication_guard_notice")),
        sa.UniqueConstraint("nonce", name=op.f("uq_publication_guard_notice_nonce")),
        sa.UniqueConstraint(
            "publication_run_id",
            "recipient_user_id",
            name=op.f("uq_publication_guard_notice_run_recipient"),
        ),
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS publication_guard_notice")
    op.drop_index("ix_publication_run_guard_release", table_name="publication_run")
    op.execute("ALTER TABLE publication_run DROP CONSTRAINT IF EXISTS ck_publication_run_state")
    op.execute(
        "ALTER TABLE publication_run DROP CONSTRAINT IF EXISTS "
        "ck_publication_run_ck_publication_run_state"
    )
    op.execute(
        "ALTER TABLE publication_run ADD CONSTRAINT ck_publication_run_state CHECK ("
        "state IN ('preparing', 'publishing', 'succeeded_automatic', 'succeeded_manual', "
        "'skipped_after_manual', 'failed', 'retry_pending', 'partially_published'))"
    )
    op.drop_column("publication_run", "decision_reason")
    op.drop_column("publication_run", "decision_by_user_id")
    op.drop_column("publication_run", "decision_at")
    op.drop_column("publication_run", "release_at")
    op.drop_constraint("ck_guild_config_publication_grace_seconds", "guild_config", type_="check")
    op.drop_column("guild_config", "publication_guard_recipient_ids")
    op.drop_column("guild_config", "publication_grace_seconds")
