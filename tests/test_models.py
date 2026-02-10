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
