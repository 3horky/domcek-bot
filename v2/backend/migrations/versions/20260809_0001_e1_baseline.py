"""Create the E1 schema baseline.

Revision ID: 0001_e1_baseline
Revises: None
Create Date: 2026-08-09
"""

from collections.abc import Sequence

revision: str = "0001_e1_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """E1 intentionally has no domain tables."""


def downgrade() -> None:
    """E1 intentionally has no domain tables."""
