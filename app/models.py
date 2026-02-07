from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric, String, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


def DecimalColumn(scale: int = 4, precision: int = 18):
    return Column(Numeric(precision, scale))


class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(sa_column=Column(String(64), unique=True))
    name: str


class Community(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    # index for faster lookups
    company_id: int = Field(foreign_key="company.id", index=True)
    code: str = Field(sa_column=Column(String(64)))
    name: str


class Building(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    community_id: int = Field(foreign_key="community.id", index=True)
    code: str
    name: str


class Unit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    building_id: int = Field(foreign_key="building.id", index=True)
    unit_no: str
    remark: Optional[str] = None


class Tenant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    mobile: Optional[str]


class Lease(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    unit_id: int = Field(foreign_key="unit.id", index=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    start_date: date
    end_date: date
    rent_amount: Decimal = Field(sa_column=DecimalColumn())
    deposit_amount: Decimal = Field(sa_column=DecimalColumn())


class Meter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    unit_id: int = Field(foreign_key="unit.id", index=True)
    kind: str  # cold_water hot_water elec
    slot: int  # 1 or 2
    serial: Optional[str]

    __table_args__ = (
        UniqueConstraint("unit_id", "kind", "slot", name="uix_unit_kind_slot"),
    )


class MeterReading(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    meter_id: int = Field(foreign_key="meter.id", index=True)
    period: str  # YYYY-MM
    reading: Decimal = Field(sa_column=DecimalColumn())
    read_at: datetime

    __table_args__ = (UniqueConstraint("meter_id", "period", name="uix_meter_period"),)


class TariffWater(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: Optional[int] = Field(foreign_key="company.id", index=True)
    community_id: Optional[int] = Field(foreign_key="community.id", index=True)
    cold_price: Decimal = Field(sa_column=DecimalColumn())
    hot_price: Decimal = Field(sa_column=DecimalColumn())


class ChargeItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str
    name: str


class Bill(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    community_id: int = Field(foreign_key="community.id", index=True)
    unit_id: int = Field(foreign_key="unit.id", index=True)
    cycle_start: date  # billing cycle start date (based on lease.start_date)
    cycle_end: date  # inclusive cycle end
    status: str = Field(default="draft")
    total_amount: Decimal = Field(sa_column=DecimalColumn())

    __table_args__ = (
        UniqueConstraint("unit_id", "cycle_start", name="uix_unit_cycle_start_bill"),
    )
    frozen_snapshot: Optional[str] = Field(default=None, sa_column=Column(String))


class BillLine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bill_id: int = Field(foreign_key="bill.id", index=True)
    charge_code: str
    amount: Decimal = Field(sa_column=DecimalColumn())
    qty: Optional[Decimal] = Field(default=None, sa_column=DecimalColumn())
    unit_price: Optional[Decimal] = Field(default=None, sa_column=DecimalColumn())


class Adjustment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bill_id: Optional[int] = Field(foreign_key="bill.id", index=True)
    reason: str
    amount: Decimal = Field(sa_column=DecimalColumn())


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(sa_column=Column(String(128), unique=True))
    password_hash: str
    role: str  # admin finance clerk


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    actor_id: Optional[int] = Field(foreign_key="user.id", index=True)
    action: str
    before: Optional[str]
    after: Optional[str]
    ip: Optional[str]
    trace_id: Optional[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AppConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str
    value: str


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
