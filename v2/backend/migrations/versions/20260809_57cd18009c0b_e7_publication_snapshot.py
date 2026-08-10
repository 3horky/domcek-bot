"""e7 publication snapshot and recovery state

Revision ID: 57cd18009c0b
Revises: 8f42d04dc7a1
Create Date: 2026-08-09 20:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "57cd18009c0b"
down_revision: str | None = "8f42d04dc7a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "publication_run",
        sa.Column(
            "composer_version", sa.String(length=64), server_default="unknown", nullable=False
        ),
    )
    op.add_column(
        "publication_run", sa.Column("intro_text", sa.Text(), server_default="", nullable=False)
    )
    op.add_column(
        "publication_run",
        sa.Column(
            "intro_prompt_version",
            sa.String(length=64),
            server_default="fallback-v1",
            nullable=False,
        ),
    )
    op.add_column(
        "publication_run",
        sa.Column("intro_used_fallback", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column("publication_run", sa.Column("outro_text", sa.Text(), nullable=True))
    op.add_column(
        "publication_run",
        sa.Column(
            "warning_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )

    op.drop_constraint(op.f("ck_publication_message_state"), "publication_message", type_="check")
    op.create_check_constraint(
        op.f("ck_publication_message_state"),
        "publication_message",
        "state IN ('pending', 'sending', 'sent', 'failed', 'uncertain')",
    )
    op.add_column("publication_message", sa.Column("part_key", sa.String(length=64), nullable=True))
    op.add_column("publication_message", sa.Column("nonce", sa.String(length=25), nullable=True))
    op.add_column("publication_message", sa.Column("content", sa.Text(), nullable=True))
    op.add_column(
        "publication_message",
        sa.Column(
            "embeds",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "publication_message",
        sa.Column(
            "allowed_mentions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "publication_message",
        sa.Column("seen_target", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "publication_message",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("publication_message", sa.Column("reaction_error", sa.Text(), nullable=True))
    op.add_column(
        "publication_message",
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE publication_message SET part_key = encode(sha256(id::text::bytea), 'hex'), "
        "nonce = left(encode(sha256(id::text::bytea), 'hex'), 25)"
    )
    op.alter_column("publication_message", "part_key", nullable=False)
    op.alter_column("publication_message", "nonce", nullable=False)

    op.create_table(
        "publication_incident",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("publication_run_id", sa.UUID(), nullable=False),
        sa.Column("publication_message_id", sa.UUID(), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('open', 'resolved')", name=op.f("ck_publication_incident_state")
        ),
        sa.ForeignKeyConstraint(["guild_id"], ["guild_config.guild_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["publication_run_id"], ["publication_run.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["publication_message_id"], ["publication_message.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_publication_incident_guild_state",
        "publication_incident",
        ["guild_id", "state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_publication_incident_guild_state", table_name="publication_incident")
    op.drop_table("publication_incident")
    op.drop_column("publication_message", "last_attempt_at")
    op.drop_column("publication_message", "reaction_error")
    op.drop_column("publication_message", "attempt_count")
    op.drop_column("publication_message", "seen_target")
    op.drop_column("publication_message", "allowed_mentions")
    op.drop_column("publication_message", "embeds")
    op.drop_column("publication_message", "content")
    op.drop_column("publication_message", "nonce")
    op.drop_column("publication_message", "part_key")
    op.drop_constraint(op.f("ck_publication_message_state"), "publication_message", type_="check")
    op.create_check_constraint(
        op.f("ck_publication_message_state"),
        "publication_message",
        "state IN ('pending', 'sent', 'failed')",
    )
    op.drop_column("publication_run", "warning_codes")
    op.drop_column("publication_run", "outro_text")
    op.drop_column("publication_run", "intro_used_fallback")
    op.drop_column("publication_run", "intro_prompt_version")
    op.drop_column("publication_run", "intro_text")
    op.drop_column("publication_run", "composer_version")
