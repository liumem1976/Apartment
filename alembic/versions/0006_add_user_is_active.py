"""add is_active to user

Revision ID: 0006_add_user_is_active
Revises: 0005_fixup_remove_duplicate_meters
Create Date: 2026-02-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_add_user_is_active"
down_revision = "0005_fixup_remove_duplicate_meters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add `is_active` column to `user` table with default True
    op.add_column(
        "user",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )


def downgrade() -> None:
    op.drop_column("user", "is_active")
