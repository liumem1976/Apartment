import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import Company


@pytest.mark.parametrize("url", ["sqlite:///:memory:"])
def test_create_and_bind_models(url):
    engine = create_engine(url, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        c = Company(code="C1", name="TestCo")
        session.add(c)
        session.commit()
        assert c.id is not None


def test_meter_unique_constraint():
    from app.models import Meter
    from sqlalchemy.exc import IntegrityError

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

        m1 = Meter(unit_id=u.id, kind="cold", slot=1)
        session.add(m1)
        session.commit()

        m2 = Meter(unit_id=u.id, kind="cold", slot=1)
        session.add(m2)
        with pytest.raises(IntegrityError):
            session.commit()
