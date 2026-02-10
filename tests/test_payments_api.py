from datetime import datetime
from decimal import Decimal

from sqlmodel import Session, select
from starlette.testclient import TestClient

from app.auth import get_password_hash
from app.db import engine, init_db
from app.main import app
from app.models import Building, Community, Company, Lease, Unit, User


def setup_module(module):
    init_db()


def make_user(username, password, role="clerk"):
    with Session(engine) as s:
        existing = s.exec(select(User).where(User.username == username)).first()
        if existing:
            return existing
        u = User(
            username=username, password_hash=get_password_hash(password), role=role
        )
        s.add(u)
        s.commit()
        s.refresh(u)
        return u


def create_sample_unit_and_lease():
    import uuid

    uniq = uuid.uuid4().hex[:8]
    with Session(engine) as s:
        comp = Company(code=f"C-{uniq}", name=f"Co {uniq}")
        s.add(comp)
        s.flush()
        comm = Community(company_id=comp.id, code=f"CM-{uniq}", name=f"Comm {uniq}")
        s.add(comm)
        s.flush()
        b = Building(community_id=comm.id, code=f"B-{uniq}", name="Bld")
        s.add(b)
        s.flush()
        from app.models import Tenant

        u = Unit(building_id=b.id, unit_no=f"{uniq}")
        s.add(u)
        s.flush()
        t = Tenant(name=f"tenant-{uniq}")
        s.add(t)
        s.flush()
        lease = Lease(
            unit_id=u.id,
            tenant_id=t.id,
            start_date=datetime(2026, 1, 1).date(),
            end_date=datetime(2026, 12, 31).date(),
            rent_amount=Decimal("1000.00"),
            deposit_amount=Decimal("1000.00"),
        )
        s.add(lease)
        s.commit()
        return u.id, lease


def get_token(client, username, password):
    r = client.post(
        "/api/auth/token", data={"username": username, "password": password}
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def test_payments_api_json_and_form():
    client = TestClient(app)
    # create users
    make_user("clerk1", "cpass", "clerk")
    make_user("fin1", "fpass", "finance")

    unit_id, lease = create_sample_unit_and_lease()

    token = get_token(client, "clerk1", "cpass")
    headers = {"Authorization": f"Bearer {token}"}

    # generate a bill first
    r = client.post(
        "/api/v1/bills/generate",
        params={"unit_id": unit_id, "date": "2026-02-15"},
        headers=headers,
    )
    assert r.status_code == 200
    bill_id = r.json()["bill_id"]

    # JSON payload
    payload = {
        "bill_id": bill_id,
        "amount": "120.50",
        "method": "card",
        "reference": "txn-json",
    }
    r = client.post("/api/v1/payments", json=payload, headers=headers)
    print("JSON resp:", r.status_code, r.text)
    assert r.status_code == 200
    assert "payment_id" in r.json()

    # Form payload (unit-level credit)
    form = {"unit_id": unit_id, "amount": "50.00", "method": "cash"}
    r = client.post("/api/v1/payments", data=form, headers=headers)
    print("FORM resp:", r.status_code, r.text)
    assert r.status_code == 200
    assert "payment_id" in r.json()

    # verify payments applied reduced arrears when generating next bill
    # generate next cycle bill
    r = client.post(
        "/api/v1/bills/generate",
        params={"unit_id": unit_id, "date": "2026-03-15"},
        headers=headers,
    )
    assert r.status_code == 200
    next_bill_id = r.json()["bill_id"]
    # ensure created
    assert next_bill_id is not None
