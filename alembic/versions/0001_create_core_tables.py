"""create core tables

Revision ID: 0001_create_core_tables
Revises:
Create Date: 2026-02-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_create_core_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=True),
    )

    op.create_table(
        "community",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255)),
        sa.Column("company_id", sa.Integer, sa.ForeignKey("company.id")),
    )

    op.create_table(
        "building",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255)),
        sa.Column("community_id", sa.Integer, sa.ForeignKey("community.id")),
    )

    op.create_table(
        "unit",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("unit_no", sa.String(length=64), nullable=False),
        sa.Column("building_id", sa.Integer, sa.ForeignKey("building.id")),
    )

    op.create_table(
        "tenant",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("mobile", sa.String(length=32)),
    )

    op.create_table(
        "lease",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("unit_id", sa.Integer, sa.ForeignKey("unit.id")),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenant.id")),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("rent_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("deposit_amount", sa.Numeric(18, 4), nullable=True),
    )

    op.create_table(
        "meter",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("unit_id", sa.Integer, sa.ForeignKey("unit.id")),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("slot", sa.Integer, nullable=False),
    )

    op.create_table(
        "meterreading",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("meter_id", sa.Integer, sa.ForeignKey("meter.id")),
        sa.Column("period", sa.String(length=16), nullable=False),
        sa.Column("reading", sa.Numeric(18, 4), nullable=False),
        sa.Column("read_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "bill",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("unit_id", sa.Integer, sa.ForeignKey("unit.id")),
        sa.Column("cycle_start", sa.Date, nullable=False),
        sa.Column("cycle_end", sa.Date, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
    )
    op.create_index(
        "ix_bill_unit_cycle", "bill", ["unit_id", "cycle_start"], unique=True
    )

    op.create_table(
        "billline",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("bill_id", sa.Integer, sa.ForeignKey("bill.id")),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
    )

    op.create_table(
        "user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(length=128), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
    )

    op.create_table(
        "auditlog",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("table_name", sa.String(length=128), nullable=False),
        sa.Column("row_id", sa.Integer, nullable=True),
        sa.Column("before", sa.Text, nullable=True),
        sa.Column("after", sa.Text, nullable=True),
        sa.Column("actor", sa.String(length=128), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("auditlog")
    op.drop_table("user")
    op.drop_table("billline")
    op.drop_index("ix_bill_unit_cycle", table_name="bill")
    op.drop_table("bill")
    op.drop_table("meterreading")
    op.drop_table("meter")
    op.drop_table("lease")
    op.drop_table("tenant")
    op.drop_table("unit")
    op.drop_table("building")
    op.drop_table("community")
    op.drop_table("company")
