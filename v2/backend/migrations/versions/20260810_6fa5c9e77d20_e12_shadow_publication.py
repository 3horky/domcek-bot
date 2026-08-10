"""e12 durable shadow publication evidence

Revision ID: 6fa5c9e77d20
Revises: 2c7f9d8b31a0
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "6fa5c9e77d20"
down_revision: str | None = "2c7f9d8b31a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shadow_publication",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("slot_key", sa.String(length=160), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("draft_sha256", sa.String(length=64), nullable=False),
        sa.Column("draft_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("warning_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "item_count >= 0", name=op.f("ck_shadow_publication_nonnegative_item_count")
        ),
        sa.CheckConstraint(
            "message_count >= 0", name=op.f("ck_shadow_publication_nonnegative_message_count")
        ),
        sa.CheckConstraint(
            "observation_count >= 1", name=op.f("ck_shadow_publication_positive_observation_count")
        ),
        sa.ForeignKeyConstraint(
            ["guild_id"],
            ["guild_config.guild_id"],
            name=op.f("fk_shadow_publication_guild_id_guild_config"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shadow_publication")),
        sa.UniqueConstraint("guild_id", "slot_key", name="shadow_publication_guild_slot"),
    )
    op.create_index(
        "ix_shadow_publication_guild_scheduled",
        "shadow_publication",
        ["guild_id", "scheduled_for"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_shadow_publication_guild_scheduled", table_name="shadow_publication")
    op.drop_table("shadow_publication")
