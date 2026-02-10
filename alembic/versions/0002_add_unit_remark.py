"""add unit.remark column

Revision ID: 0002_add_unit_remark
Revises: 0001_create_core_tables
Create Date: 2026-02-08 07:10:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_add_unit_remark"
down_revision = "0001_create_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # add remark column to unit for imports compatibility
    op.add_column("unit", sa.Column("remark", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("unit", "remark")
