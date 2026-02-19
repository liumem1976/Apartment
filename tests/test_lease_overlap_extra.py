from datetime import date

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import Lease, Unit, Tenant, Company, Community, Building
from app.models import assert_no_lease_overlap


def setup_minimal(session: Session):
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

    t = Tenant(name="T1")
    session.add(t)
    session.commit()

    return u, t


@pytest.fixture
def engine():
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(e)
    return e


def test_adjacent_non_overlap(engine):
    with Session(engine) as s:
        u, t = setup_minimal(s)
        # existing lease ends on Jan 31
        lease = Lease(unit_id=u.id, tenant_id=t.id, start_date=date(2023, 1, 1), end_date=date(2023, 1, 31))
        s.add(lease)
        s.commit()

        # new lease starts on Feb 1 -> adjacent, should NOT overlap
        assert_no_lease_overlap(s, u.id, date(2023, 2, 1), date(2023, 2, 28))


def test_overlap_start_inside(engine):
    with Session(engine) as s:
        u, t = setup_minimal(s)
        lease = Lease(unit_id=u.id, tenant_id=t.id, start_date=date(2023, 3, 1), end_date=date(2023, 3, 31))
        s.add(lease)
        s.commit()

        # new lease starts inside existing -> should raise
        with pytest.raises(ValueError):
            assert_no_lease_overlap(s, u.id, date(2023, 3, 15), date(2023, 4, 15))


def test_existing_open_ended(engine):
    with Session(engine) as s:
        u, t = setup_minimal(s)
        # existing lease has no end_date (open-ended)
        lease = Lease(unit_id=u.id, tenant_id=t.id, start_date=date(2023, 5, 1), end_date=None)
        s.add(lease)
        s.commit()

        # any new lease overlapping start_date >= 2023-05-01 should raise
        with pytest.raises(ValueError):
            assert_no_lease_overlap(s, u.id, date(2023, 6, 1), date(2023, 6, 30))


def test_exclude_id_allows_update(engine):
    with Session(engine) as s:
        u, t = setup_minimal(s)
        lease = Lease(unit_id=u.id, tenant_id=t.id, start_date=date(2023, 7, 1), end_date=date(2023, 7, 31))
        s.add(lease)
        s.commit()

        # updating the same lease (exclude_id) should not raise
        assert_no_lease_overlap(s, u.id, date(2023, 7, 1), date(2023, 7, 31), exclude_id=lease.id)


def test_same_day_start_equals_existing_end_overlap(engine):
    with Session(engine) as s:
        u, t = setup_minimal(s)
        # existing lease ends on Jan 31
        lease = Lease(unit_id=u.id, tenant_id=t.id, start_date=date(2023, 1, 1), end_date=date(2023, 1, 31))
        s.add(lease)
        s.commit()

        # new lease starts on Jan 31 (same day) -> considered overlap
        with pytest.raises(ValueError):
            assert_no_lease_overlap(s, u.id, date(2023, 1, 31), date(2023, 2, 28))


def test_new_lease_before_existing_no_overlap(engine):
    with Session(engine) as s:
        u, t = setup_minimal(s)
        # existing lease starts on March 10
        lease = Lease(unit_id=u.id, tenant_id=t.id, start_date=date(2023, 3, 10), end_date=date(2023, 3, 20))
        s.add(lease)
        s.commit()

        # new lease ends before existing starts -> no overlap
        assert_no_lease_overlap(s, u.id, date(2023, 2, 1), date(2023, 3, 9))


def test_cross_month_and_year_non_overlap(engine):
    with Session(engine) as s:
        u, t = setup_minimal(s)
        # existing lease spans year boundary
        lease = Lease(unit_id=u.id, tenant_id=t.id, start_date=date(2023, 12, 15), end_date=date(2024, 1, 15))
        s.add(lease)
        s.commit()

        # new lease starts after Jan 15 -> no overlap
        assert_no_lease_overlap(s, u.id, date(2024, 1, 16), date(2024, 2, 15))


def test_new_lease_covers_existing(engine):
    with Session(engine) as s:
        u, t = setup_minimal(s)
        # existing short lease
        lease = Lease(unit_id=u.id, tenant_id=t.id, start_date=date(2023, 9, 10), end_date=date(2023, 9, 20))
        s.add(lease)
        s.commit()

        # new lease fully covers existing -> overlap
        with pytest.raises(ValueError):
            assert_no_lease_overlap(s, u.id, date(2023, 9, 1), date(2023, 10, 1))
