from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import relationship as sa_relationship
from sqlmodel import Field, Relationship, Session as SQLSession, SQLModel, select


class BillStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    issued = "issued"
    void = "void"


class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, nullable=False)
    name: str
    communities: List["Community"] = Relationship(
        back_populates="company",
        sa_relationship=sa_relationship("Community", back_populates="company"),
    )


class Community(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(nullable=False)
    name: str
    company_id: int = Field(foreign_key="company.id")
    company: Optional["Company"] = Relationship(
        back_populates="communities",
        sa_relationship=sa_relationship("Company", back_populates="communities"),
    )
    buildings: List["Building"] = Relationship(
        back_populates="community",
        sa_relationship=sa_relationship("Building", back_populates="community"),
    )


class Building(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(nullable=False)
    name: Optional[str]
    community_id: int = Field(foreign_key="community.id")
    community: Optional["Community"] = Relationship(
        back_populates="buildings",
        sa_relationship=sa_relationship("Community", back_populates="buildings"),
    )
    units: List["Unit"] = Relationship(
        back_populates="building",
        sa_relationship=sa_relationship("Unit", back_populates="building"),
    )


class Unit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    unit_no: str = Field(nullable=False)
    remark: Optional[str] = Field(default=None)
    building_id: int = Field(foreign_key="building.id")
    building: Optional["Building"] = Relationship(
        back_populates="units",
        sa_relationship=sa_relationship("Building", back_populates="units"),
    )


class Tenant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    mobile: Optional[str]
    leases: List["Lease"] = Relationship(
        back_populates="tenant",
        sa_relationship=sa_relationship("Lease", back_populates="tenant"),
    )


class Lease(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    unit_id: int = Field(foreign_key="unit.id")
    tenant_id: int = Field(foreign_key="tenant.id")
    start_date: date
    end_date: Optional[date]
    rent_amount: Decimal = Field(
        default=Decimal("0.0"),
        sa_column=Column("rent_amount", Numeric(18, 4), nullable=True),
    )
    deposit_amount: Decimal = Field(default=Decimal("0.0"))
    tenant: Optional["Tenant"] = Relationship(
        back_populates="leases",
        sa_relationship=sa_relationship("Tenant", back_populates="leases"),
    )


class Meter(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("unit_id", "kind", "slot", name="uq_meter_unit_kind_slot"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    unit_id: int = Field(foreign_key="unit.id")
    kind: str = Field(nullable=False)  # cold_water/hot_water
    slot: int = Field(default=1)


class MeterReading(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    meter_id: int = Field(foreign_key="meter.id")
    period: str = Field(nullable=False, index=True)
    reading: Decimal = Field(default=Decimal("0.0"))
    read_at: Optional[datetime]


class TariffWater(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: Optional[int] = Field(default=None, foreign_key="company.id")
    community_id: Optional[int] = Field(default=None, foreign_key="community.id")
    cold_price: Decimal = Field(default=Decimal("0.0"))
    hot_price: Decimal = Field(default=Decimal("0.0"))


class ChargeItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(nullable=False, unique=True)
    description: Optional[str]


class Bill(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("unit_id", "cycle_start", name="uq_bill_unit_cycle"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    unit_id: int = Field(foreign_key="unit.id")
    cycle_start: date
    cycle_end: date
    status: BillStatus = Field(sa_column=Column("status", Text, nullable=False))
    # alignment fields expected by runtime code (nullable to avoid breaking existing rows)
    company_id: Optional[int] = Field(
        default=None, sa_column=Column("company_id", Integer, nullable=True)
    )
    community_id: Optional[int] = Field(
        default=None, sa_column=Column("community_id", Integer, nullable=True)
    )
    total_amount: Decimal = Field(
        default=Decimal("0.0"),
        sa_column=Column("total_amount", Numeric(18, 4), nullable=True),
    )
    frozen_snapshot: Optional[str] = Field(
        default=None, sa_column=Column("frozen_snapshot", Text, nullable=True)
    )
    lines: List["BillLine"] = Relationship(
        back_populates="bill",
        sa_relationship=sa_relationship("BillLine", back_populates="bill"),
    )


class BillLine(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    bill_id: int = Field(foreign_key="bill.id")
    item_code: str = Field(nullable=False)
    qty: Decimal = Field(default=Decimal("1.0"))
    unit_price: Decimal = Field(default=Decimal("0.0"))
    amount: Decimal = Field(default=Decimal("0.0"))
    # runtime code expects `charge_code`; add as nullable for compatibility
    charge_code: Optional[str] = Field(
        default=None, sa_column=Column("charge_code", Text, nullable=True)
    )
    bill: Optional["Bill"] = Relationship(
        back_populates="lines",
        sa_relationship=sa_relationship("Bill", back_populates="lines"),
    )


class Adjustment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bill_line_id: Optional[int] = Field(default=None, foreign_key="billline.id")
    delta: Decimal = Field(default=Decimal("0.0"))
    reason: Optional[str]


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(nullable=False, unique=True)
    password_hash: str
    role: str


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # default to empty string so existing DB schemas with NOT NULL
    # constraints still accept inserts from older code paths
    table_name: str = Field(default="")
    row_id: Optional[int]
    before: Optional[str]
    after: Optional[str]
    actor: Optional[str]
    ip: Optional[str]
    trace_id: Optional[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AppConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(nullable=False, unique=True)
    value: Optional[str]


class ImportBatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    kind: str  # rooms | leases
    status: str = Field(default="pending")  # pending, processing, done, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[str] = Field(default=None, sa_column=Column(Text))
    errors: Optional[str] = Field(default=None, sa_column=Column(Text))


def assert_no_lease_overlap(session: SQLSession, unit_id: int, start_date, end_date, exclude_id: Optional[int] = None) -> None:
    """Raise ValueError if a lease for the same unit overlaps the given period.

    Overlap definition: existing.start <= end_date and (existing.end is None or existing.end >= start_date)
    Treat None as open-ended.
    """
    # no local imports required here
    stmt = select(Lease).where(Lease.unit_id == unit_id)
    if exclude_id is not None:
        stmt = stmt.where(Lease.id != exclude_id)

    existing = session.exec(stmt).all()
    for ex in existing:
        ex_start = ex.start_date
        ex_end = ex.end_date
        # normalize None as open-ended
        if ex_end is None:
            # any start_date <= ex_end(open) => overlap if ex_start <= end_date or end_date is None
            if end_date is None or ex_start <= end_date:
                if start_date is None or ex_start <= end_date:
                    raise ValueError(f"Lease overlaps existing lease id={ex.id}")
        else:
            # both ends present
            if (ex_start <= (end_date if end_date is not None else ex_end)) and (
                (start_date if start_date is not None else ex_start) <= ex_end
            ):
                raise ValueError(f"Lease overlaps existing lease id={ex.id}")
