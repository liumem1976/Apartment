from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine


def test_bill_unique_constraint_and_decimal_precision():
    from app.models import Bill, BillLine
    from sqlalchemy.exc import IntegrityError

    from datetime import date

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # create referenced company/community/building/unit to satisfy FKs
        from app.models import Company, Community, Building, Unit

        comp = Company(code="C1", name="Co")
        session.add(comp)
        session.commit()

        comm = Community(code="CM1", name="Comm", company_id=comp.id)
        session.add(comm)
        session.commit()

        bld = Building(code="B1", name="B", community_id=comm.id)
        session.add(bld)
        session.commit()

        u = Unit(unit_no="U1", building_id=bld.id)
        session.add(u)
        session.commit()

        b1 = Bill(unit_id=u.id, cycle_start=date(2026, 2, 1), cycle_end=date(2026, 2, 28), status="draft", total_amount=Decimal("1234.5678"))
        session.add(b1)
        session.commit()

        bl = BillLine(bill_id=b1.id, item_code="water", qty=Decimal("1.0"), unit_price=Decimal("1234.5678"), amount=Decimal("1234.5678"))
        session.add(bl)
        session.commit()

        # Bill unique constraint: same unit_id and cycle_start should violate
        b2 = Bill(unit_id=u.id, cycle_start=date(2026, 2, 1), cycle_end=date(2026, 2, 28), status="draft")
        session.add(b2)
        with pytest.raises(IntegrityError):
            session.commit()
        # rollback the failed transaction before further operations
        session.rollback()

        # Check decimal precision preserved when reading back
        session.refresh(b1)
        assert round(b1.total_amount, 4) == Decimal("1234.5678")
