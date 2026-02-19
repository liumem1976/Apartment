"""add bill template tables and link bill.template_id

Revision ID: 0007_add_bill_templates
Revises: 0006_add_user_is_active
Create Date: 2026-02-19 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007_add_bill_templates"
down_revision = "0006_add_user_is_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bill_template table
    op.create_table(
        "billtemplate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # Create bill_template_line table
    op.create_table(
        "billtemplateline",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("billtemplate.id"), nullable=False),
        sa.Column("charge_item_id", sa.Integer(), sa.ForeignKey("chargeitem.id"), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=True),
    )

    # Add template_id to existing bill table (nullable for compatibility)
    op.add_column(
        "bill",
        sa.Column("template_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    # Remove template_id from bill
    op.drop_column("bill", "template_id")

    # Drop bill_template_line and bill_template tables
    op.drop_table("billtemplateline")
    op.drop_table("billtemplate")
