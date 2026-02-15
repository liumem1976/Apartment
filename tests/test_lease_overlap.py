from datetime import date

import pytest
from sqlmodel import Session, SQLModel, create_engine


def test_lease_overlap_detection():
    from app.models import (
        Building,
        Community,
        Company,
        Lease,
        Tenant,
        Unit,
        assert_no_lease_overlap,
    )

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
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

        tenant = Tenant(name="T1")
        session.add(tenant)
        session.commit()

        # existing lease covers 2026-01-01 .. 2026-06-30
        l1 = Lease(
            unit_id=u.id,
            tenant_id=tenant.id,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )
        session.add(l1)
        session.commit()

        # overlapping lease (starts before l1 ends)
        with pytest.raises(ValueError):
            assert_no_lease_overlap(session, u.id, date(2026, 6, 1), date(2026, 12, 31))

        # non-overlapping lease (starts after l1 ends)
        assert_no_lease_overlap(session, u.id, date(2026, 7, 1), date(2026, 12, 31))
