"""merge heads for PR A

Revision ID: 0003_merge_heads
Revises: 0001_add_payment,0002_add_bill_fields,0002_add_unit_remark
Create Date: 2026-02-08 08:00:00.000000
"""

# revision identifiers, used by Alembic.
revision = "0003_merge_heads"
down_revision = (
    "0001_add_payment",
    "0002_add_bill_fields",
    "0002_add_unit_remark",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision: no schema changes. This ties together parallel heads.
    pass


def downgrade() -> None:
    # No-op downgrade for merge revision.
    pass
