from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.db import init_db, engine
from app.models import User, Company, Community, Building, Unit, Tenant, Lease
from app.auth import get_password_hash


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

        comm = session.exec(select(Community).where(Community.code == "CM1", Community.company_id == company.id)).first()
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
            lease = Lease(unit_id=u.id, tenant_id=t.id, start_date=date(2026, 2, 15), end_date=date(2027, 2, 14), rent_amount=1000, deposit_amount=1000)
            session.add(lease)
        session.commit()
        return u.id, lease


def test_full_bill_lifecycle():
    client = TestClient(app)
    clerk = make_user("clerk1", "cpass", "clerk")
    finance = make_user("fin1", "fpass", "finance")
    admin = make_user("admin1", "apass", "admin")

    unit_id, lease = create_sample_unit_and_lease()

    # create clerk token
    r = client.post("/api/auth/token", data={"username": "clerk1", "password": "cpass"})
    assert r.status_code == 200
    clerk_token = r.json()["access_token"]

    # remove existing bills for the unit to ensure fresh draft
    from app.models import Bill, BillLine
    from sqlalchemy import delete
    with Session(engine) as s:
        bills = s.exec(select(Bill).where(Bill.unit_id == unit_id)).all()
        for b in bills:
            s.exec(delete(BillLine).where(BillLine.bill_id == b.id))
            s.exec(delete(Bill).where(Bill.id == b.id))
        s.commit()

    # generate bill
    r = client.post("/api/v1/bills/generate", params={"unit_id": unit_id, "date": "2026-02-15"}, headers={"Authorization": f"Bearer {clerk_token}"})
    assert r.status_code == 200
    bill_id = r.json()["bill_id"]

    # submit
    r = client.post(f"/api/v1/bills/{bill_id}/submit", headers={"Authorization": f"Bearer {clerk_token}"})
    assert r.status_code == 200 and r.json()["status"] == "submitted"

    # finance approve
    r = client.post("/api/auth/token", data={"username": "fin1", "password": "fpass"})
    fin_token = r.json()["access_token"]
    r = client.post(f"/api/v1/bills/{bill_id}/approve", headers={"Authorization": f"Bearer {fin_token}"})
    assert r.status_code == 200 and r.json()["status"] == "approved"

    # issue
    r = client.post(f"/api/v1/bills/{bill_id}/issue", headers={"Authorization": f"Bearer {fin_token}"})
    assert r.status_code == 200 and r.json()["status"] == "issued"

    # void (admin)
    r = client.post("/api/auth/token", data={"username": "admin1", "password": "apass"})
    admin_token = r.json()["access_token"]
    r = client.post(f"/api/v1/bills/{bill_id}/void", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200 and r.json()["status"] == "void"
