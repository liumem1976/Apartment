from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint, Column, Numeric, Text, DateTime, Integer
from enum import Enum


class BillStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    issued = "issued"
    void = "void"


class Company(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, nullable=False)
    name: str
    communities: List["Community"] = Relationship(back_populates="company")


class Community(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(nullable=False)
    name: str
    company_id: int = Field(foreign_key="company.id")
    company: Optional[Company] = Relationship(back_populates="communities")
    buildings: List["Building"] = Relationship(back_populates="community")


class Building(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(nullable=False)
    name: Optional[str]
    community_id: int = Field(foreign_key="community.id")
    community: Optional[Community] = Relationship(back_populates="buildings")
    units: List["Unit"] = Relationship(back_populates="building")


class Unit(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    unit_no: str = Field(nullable=False)
    building_id: int = Field(foreign_key="building.id")
    building: Optional[Building] = Relationship(back_populates="units")


class Tenant(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    mobile: Optional[str]
    leases: List["Lease"] = Relationship(back_populates="tenant")


class Lease(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    unit_id: int = Field(foreign_key="unit.id")
    tenant_id: int = Field(foreign_key="tenant.id")
    start_date: date
    end_date: Optional[date]
    rent_amount: Decimal = Field(default=Decimal("0.0"), sa_column=Column("rent_amount", Numeric(18, 4), nullable=True))
    deposit_amount: Decimal = Field(default=Decimal("0.0"))
    tenant: Optional[Tenant] = Relationship(back_populates="leases")


class Meter(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    unit_id: int = Field(foreign_key="unit.id")
    kind: str = Field(nullable=False)  # cold_water/hot_water
    slot: int = Field(default=1)


class MeterReading(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    meter_id: int = Field(foreign_key="meter.id")
    period: str = Field(nullable=False, index=True)
    reading: Decimal = Field(default=Decimal("0.0"))
    read_at: Optional[datetime]


class TariffWater(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: Optional[int] = Field(default=None, foreign_key="company.id")
    community_id: Optional[int] = Field(default=None, foreign_key="community.id")
    cold_price: Decimal = Field(default=Decimal("0.0"))
    hot_price: Decimal = Field(default=Decimal("0.0"))


class ChargeItem(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(nullable=False, unique=True)
    description: Optional[str]


class Bill(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("unit_id", "cycle_start", name="uq_bill_unit_cycle"), {"extend_existing": True})
    id: Optional[int] = Field(default=None, primary_key=True)
    unit_id: int = Field(foreign_key="unit.id")
    cycle_start: date
    cycle_end: date
    status: BillStatus = Field(sa_column=Column("status", Text, nullable=False))
    # alignment fields expected by runtime code (nullable to avoid breaking existing rows)
    company_id: Optional[int] = Field(default=None, sa_column=Column("company_id", Integer, nullable=True))
    community_id: Optional[int] = Field(default=None, sa_column=Column("community_id", Integer, nullable=True))
    total_amount: Decimal = Field(default=Decimal("0.0"), sa_column=Column("total_amount", Numeric(18, 4), nullable=True))
    frozen_snapshot: Optional[str] = Field(default=None, sa_column=Column("frozen_snapshot", Text, nullable=True))
    lines: List["BillLine"] = Relationship(back_populates="bill")


class BillLine(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    bill_id: int = Field(foreign_key="bill.id")
    item_code: str = Field(nullable=False)
    qty: Decimal = Field(default=Decimal("1.0"))
    unit_price: Decimal = Field(default=Decimal("0.0"))
    amount: Decimal = Field(default=Decimal("0.0"))
    # runtime code expects `charge_code`; add as nullable for compatibility
    charge_code: Optional[str] = Field(default=None, sa_column=Column("charge_code", Text, nullable=True), index=True)
    bill: Optional[Bill] = Relationship(back_populates="lines")


class Adjustment(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    bill_line_id: Optional[int] = Field(default=None, foreign_key="billline.id")
    delta: Decimal = Field(default=Decimal("0.0"))
    reason: Optional[str]


class User(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(nullable=False, unique=True)
    password_hash: str
    role: str


class AuditLog(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    table_name: str
    row_id: Optional[int]
    before: Optional[str]
    after: Optional[str]
    actor: Optional[str]
    ip: Optional[str]
    trace_id: Optional[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AppConfig(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(nullable=False, unique=True)
    value: Optional[str]
