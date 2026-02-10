"""add bill/company/community fields and charge_code

Revision ID: 0002_add_bill_fields
Revises: 0001_create_core_tables
Create Date: 2026-02-08 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_bill_fields"
down_revision = "0001_create_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable columns to avoid breaking existing data
    op.add_column("bill", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("bill", sa.Column("community_id", sa.Integer(), nullable=True))
    op.add_column("bill", sa.Column("total_amount", sa.Numeric(18, 4), nullable=True))
    op.add_column("bill", sa.Column("frozen_snapshot", sa.Text(), nullable=True))

    op.add_column("billline", sa.Column("charge_code", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("billline", "charge_code")

    op.drop_column("bill", "frozen_snapshot")
    op.drop_column("bill", "total_amount")
    op.drop_column("bill", "community_id")
    op.drop_column("bill", "company_id")
