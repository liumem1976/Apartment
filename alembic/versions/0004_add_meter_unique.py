"""add unique constraint for meter (unit_id, kind, slot)

Revision ID: 0004_add_meter_unique
Revises: 0003_merge_heads
Create Date: 2026-02-11 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_add_meter_unique"
down_revision = "0003_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_meter_unit_kind_slot",
        "meter",
        ["unit_id", "kind", "slot"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_meter_unit_kind_slot", table_name="meter")
