import calendar
from datetime import date, timedelta
from typing import List, Optional, Tuple

from sqlmodel import Session, select

from .db import engine
from .models import AuditLog, Bill, BillLine, Lease


def _add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def compute_billing_cycle(lease_start: date, target: date) -> Tuple[date, date]:
    # billing cycles start on lease_start.day each calendar month
    day = lease_start.day
    try:
        candidate = date(target.year, target.month, day)
    except ValueError:
        # day might not exist in month (e.g., 31) -> clamp to last day
        last = calendar.monthrange(target.year, target.month)[1]
        candidate = date(target.year, target.month, last)

    if target >= candidate:
        cycle_start = candidate
    else:
        # previous month
        prev_month = _add_months(candidate, -1)
        cycle_start = prev_month

    next_start = _add_months(cycle_start, 1)
    cycle_end = next_start - timedelta(days=1)
    return cycle_start, cycle_end


def generate_bill_for_unit(
    unit_id: int, target_date: date, actor_id: Optional[int] = None
) -> Bill:
    with Session(engine) as session:
        lease = session.exec(select(Lease).where(Lease.unit_id == unit_id)).first()
        if not lease:
            raise ValueError("No lease for unit")
        cycle_start, cycle_end = compute_billing_cycle(lease.start_date, target_date)
        # ensure uniqueness
        existing = session.exec(
            select(Bill).where(Bill.unit_id == unit_id, Bill.cycle_start == cycle_start)
        ).first()
        if existing:
            return existing

        # determine company/community via unit->building->community->company
        from .models import Building, Community, Company, Unit

        unit = session.get(Unit, unit_id)
        b = session.get(Building, unit.building_id)
        comm = session.get(Community, b.community_id)
        comp = session.get(Company, comm.company_id)

        bill = Bill(
            company_id=comp.id,
            community_id=comm.id,
            unit_id=unit_id,
            cycle_start=cycle_start,
            cycle_end=cycle_end,
            status="draft",
            total_amount=0,
        )
        session.add(bill)
        session.flush()

        # rent line (store unit_price and qty so it can be frozen later)
        rent_line = BillLine(
            bill_id=bill.id,
            item_code="rent",
            charge_code="rent",
            amount=lease.rent_amount,
            qty=1,
            unit_price=lease.rent_amount,
        )
        session.add(rent_line)

        # compute total
        bill.total_amount = lease.rent_amount
        session.add(bill)

        # audit
        audit = AuditLog(
            actor_id=actor_id,
            action="create_bill",
            before=None,
            after=f"bill:{bill.id}",
        )
        session.add(audit)

        session.commit()
        session.refresh(bill)
        return bill


def generate_batch_for_company(
    company_id: int, target_date: date, actor_id: Optional[int] = None
) -> List[Bill]:
    bills = []
    with Session(engine) as session:
        leases = session.exec(select(Lease)).all()
        for lease in leases:
            try:
                bill = generate_bill_for_unit(
                    lease.unit_id, target_date, actor_id=actor_id
                )
                bills.append(bill)
            except Exception:
                session.rollback()
                raise
    return bills
