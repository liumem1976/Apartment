from starlette.testclient import TestClient
from sqlmodel import Session, select

from app.auth import get_password_hash
from app.db import engine, init_db
from app.main import app
from app.models import Company, Community, Building, Unit, Tenant, Lease, User, Bill, BillLine


def setup_module(module):
    init_db()


def make_user(username, password, role):
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == username)).first()
        if existing:
            return existing
        u = User(username=username, password_hash=get_password_hash(password), role=role)
        session.add(u)
        session.commit()
        return u


def create_sample_unit_and_lease():
    from datetime import date

    with Session(engine) as session:
        company = session.exec(select(Company).where(Company.code == "C1")).first()
        if not company:
            company = Company(code="C1", name="Co1")
            session.add(company)
            session.flush()

        comm = session.exec(
            select(Community).where(Community.code == "CM1", Community.company_id == company.id)
        ).first()
        if not comm:
            comm = Community(company_id=company.id, code="CM1", name="Comm1")
            session.add(comm)
            session.flush()

        b = session.exec(select(Building).where(Building.code == "B1", Building.community_id == comm.id)).first()
        if not b:
            b = Building(community_id=comm.id, code="B1", name="B1")
            session.add(b)
            session.flush()

        u = session.exec(select(Unit).where(Unit.unit_no == "101", Unit.building_id == b.id)).first()
        if not u:
            u = Unit(building_id=b.id, unit_no="101")
            session.add(u)
            session.flush()

        t = session.exec(select(Tenant).where(Tenant.name == "T1")).first()
        if not t:
            t = Tenant(name="T1", mobile="13800000000")
            session.add(t)
            session.flush()

        lease = session.exec(select(Lease).where(Lease.unit_id == u.id)).first()
        if not lease:
            lease = Lease(
                unit_id=u.id,
                tenant_id=t.id,
                start_date=date(2026, 2, 15),
                end_date=date(2027, 2, 14),
                rent_amount=1000,
                deposit_amount=1000,
            )
            session.add(lease)
        session.commit()
        return u.id, lease


def test_export_bill_csv():
    client = TestClient(app)
    make_user("clerk2", "cpass", "clerk")
    unit_id, lease = create_sample_unit_and_lease()

    # create clerk token
    r = client.post("/api/auth/token", data={"username": "clerk2", "password": "cpass"})
    assert r.status_code == 200
    clerk_token = r.json()["access_token"]

    # remove existing bills for the unit
    from sqlalchemy import delete

    with Session(engine) as s:
        bills = s.exec(select(Bill).where(Bill.unit_id == unit_id)).all()
        for b in bills:
            s.exec(delete(BillLine).where(BillLine.bill_id == b.id))
            s.exec(delete(Bill).where(Bill.id == b.id))
        s.commit()

    # generate bill
    r = client.post(
        "/api/v1/bills/generate",
        params={"unit_id": unit_id, "date": "2026-02-15"},
        headers={"Authorization": f"Bearer {clerk_token}"},
    )
    assert r.status_code == 200
    bill_id = r.json()["bill_id"]

    # export CSV
    r = client.get(f"/api/v1/bills/{bill_id}/export", params={"export": "csv"}, headers={"Authorization": f"Bearer {clerk_token}"})
    assert r.status_code == 200
    assert r.headers.get("content-disposition") is not None
    text = r.content.decode("utf-8")
    assert "charge_code" in text
    assert "rent" in text
    assert "1000" in text
