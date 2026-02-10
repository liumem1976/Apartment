"""add payment table

Revision ID: 0001_add_payment
Revises:
Create Date: 2026-02-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_add_payment"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "bill_id",
            sa.Integer(),
            sa.ForeignKey("bill.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "unit_id",
            sa.Integer(),
            sa.ForeignKey("unit.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("method", sa.String(64), nullable=True),
        sa.Column("reference", sa.String(128), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_payment_bill_id", "payment", ["bill_id"])
    op.create_index("ix_payment_unit_id", "payment", ["unit_id"])


def downgrade():
    op.drop_index("ix_payment_unit_id", table_name="payment")
    op.drop_index("ix_payment_bill_id", table_name="payment")
    op.drop_table("payment")
