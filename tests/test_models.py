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
        m1 = Meter(unit_id=1, kind="cold", slot=1)
        session.add(m1)
        session.commit()

        m2 = Meter(unit_id=1, kind="cold", slot=1)
        session.add(m2)
        with pytest.raises(IntegrityError):
            session.commit()
