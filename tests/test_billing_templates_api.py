from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth import get_password_hash
from datetime import date
from app.db import engine
from app.main import app
from app.models import (
    User,
    ChargeItem,
    BillTemplate,
    BillTemplateLine,
    Company,
    Community,
    Building,
    Unit,
    Lease,
    Bill,
    BillLine,
)


client = TestClient(app)


def make_user(username: str, password: str, role: str):
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == username)).first()
        if not existing:
            u = User(username=username, password_hash=get_password_hash(password), role=role)
            session.add(u)
            session.commit()
            session.refresh(u)
            return u
        return existing


def get_token(username: str, password: str):
    r = client.post("/api/auth/token", data={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def ensure_chargeitem_table():
    # create minimal chargeitem table if migrations didn't create it
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS chargeitem (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, description TEXT)"
            )
        )


def test_admin_crud_and_rbac():
    # prepare users
    make_user("tmpl_admin", "pw", "admin")
    make_user("tmpl_clerk", "pw", "clerk")
    make_user("tmpl_sales", "pw", "sales")

    admin_tok = get_token("tmpl_admin", "pw")
    clerk_tok = get_token("tmpl_clerk", "pw")
    sales_tok = get_token("tmpl_sales", "pw")

    # prepare charge items
    ensure_chargeitem_table()
    with Session(engine) as session:
        ci1 = session.exec(select(ChargeItem).where(ChargeItem.code == "c1")).first()
        if not ci1:
            ci1 = ChargeItem(code="c1", description="Charge 1")
            session.add(ci1)
        ci2 = session.exec(select(ChargeItem).where(ChargeItem.code == "c2")).first()
        if not ci2:
            ci2 = ChargeItem(code="c2", description="Charge 2")
            session.add(ci2)
        session.commit()
        session.refresh(ci1)
        session.refresh(ci2)

    # admin creates a template
    payload = {
        "name": "T1",
        "description": "desc",
        "is_active": True,
        "items": [
            {"charge_item_id": ci1.id, "is_required": True, "sort_order": 2, "note": "n1"},
            {"charge_item_id": ci2.id, "is_required": False, "sort_order": 1, "note": "n2"},
        ],
    }
    r = client.post("/api/v1/templates/", json=payload, headers={"Authorization": f"Bearer {admin_tok}"})
    assert r.status_code == 200
    t = r.json()
    tid = t["id"] if isinstance(t, list) else t.get("id")
    # retrieve
    r2 = client.get(f"/api/v1/templates/{tid}", headers={"Authorization": f"Bearer {admin_tok}"})
    assert r2.status_code == 200
    data = r2.json()
    assert data["name"] == "T1"
    # items should be present and we expect them sorted by sort_order when instantiated
    assert len(data["items"]) == 2

    # clerk and sales cannot create/update/delete
    r_clerk_create = client.post("/api/v1/templates/", json=payload, headers={"Authorization": f"Bearer {clerk_tok}"})
    assert r_clerk_create.status_code == 403
    r_sales_create = client.post("/api/v1/templates/", json=payload, headers={"Authorization": f"Bearer {sales_tok}"})
    assert r_sales_create.status_code == 403

    # admin updates template
    upd = {"name": "T1-updated"}
    r_upd = client.put(f"/api/v1/templates/{tid}", json=upd, headers={"Authorization": f"Bearer {admin_tok}"})
    assert r_upd.status_code == 200
    assert r_upd.json()["name"] == "T1-updated"

    # admin delete
    r_del = client.delete(f"/api/v1/templates/{tid}", headers={"Authorization": f"Bearer {admin_tok}"})
    assert r_del.status_code == 200


def test_list_and_instantiate_by_clerk_and_sales():
    # setup company/community/building/unit/lease
    with Session(engine) as session:
        comp = Company(code="CX", name="CompX")
        session.add(comp)
        session.commit()
        session.refresh(comp)
        comm = Community(code="CM", name="Comm", company_id=comp.id)
        session.add(comm)
        session.commit()
        session.refresh(comm)
        b = Building(code="B1", name="Bldg", community_id=comm.id)
        session.add(b)
        session.commit()
        session.refresh(b)
        unit = Unit(unit_no="U1", building_id=b.id)
        session.add(unit)
        session.commit()
        session.refresh(unit)
        unit_id = unit.id
        # lease start at 2026-02-01
        lease = Lease(unit_id=unit.id, tenant_id=None, start_date=date(2026, 2, 1), end_date=None, rent_amount=0)
        session.add(lease)
        session.commit()
        session.refresh(lease)

        # prepare charge items and template
        ensure_chargeitem_table()
        ci1 = session.exec(select(ChargeItem).where(ChargeItem.code == "ciA")).first()
        if not ci1:
            ci1 = ChargeItem(code="ciA", description="A")
            session.add(ci1)
        ci2 = session.exec(select(ChargeItem).where(ChargeItem.code == "ciB")).first()
        if not ci2:
            ci2 = ChargeItem(code="ciB", description="B")
            session.add(ci2)
        session.commit()
        session.refresh(ci1)
        session.refresh(ci2)

        tmpl = BillTemplate(name="TempInst", description="for inst", is_active=True, created_by=1)
        session.add(tmpl)
        session.commit()
        session.refresh(tmpl)
        l1 = BillTemplateLine(template_id=tmpl.id, charge_item_id=ci1.id, is_required=True, sort_order=1)
        l2 = BillTemplateLine(template_id=tmpl.id, charge_item_id=ci2.id, is_required=False, sort_order=2)
        session.add(l1)
        session.add(l2)
        session.commit()
        session.refresh(l1)
        session.refresh(l2)

        tid = tmpl.id


    # create users and tokens
    make_user("i_admin", "pw", "admin")
    make_user("i_clerk", "pw", "clerk")
    make_user("i_sales", "pw", "sales")
    clerk_tok = get_token("i_clerk", "pw")
    sales_tok = get_token("i_sales", "pw")

    # clerk and sales can list
    r_list_c = client.get("/api/v1/templates/", headers={"Authorization": f"Bearer {clerk_tok}"})
    assert r_list_c.status_code == 200
    r_list_s = client.get("/api/v1/templates/", headers={"Authorization": f"Bearer {sales_tok}"})
    assert r_list_s.status_code == 200

    # instantiate as sales
    r_inst = client.post(f"/api/v1/templates/{tid}/instantiate", params={"unit_id": unit_id, "date": "2026-02-15"}, headers={"Authorization": f"Bearer {sales_tok}"})
    assert r_inst.status_code == 200
    j = r_inst.json()
    assert "bill_id" in j
    bill_id = j["bill_id"]

    # verify bill and lines
    with Session(engine) as session:
        bill = session.get(Bill, bill_id)
        assert bill is not None
        assert bill.template_id == tid
        lines = session.exec(select(BillLine).where(BillLine.bill_id == bill.id)).all()
        assert len(lines) == 2
        # map codes to template lines
        codes = [ln.item_code for ln in lines]
        assert any("ciA" in c for c in codes)
        assert any("ciB" in c for c in codes)
        # amounts initialized to 0
        for ln in lines:
            assert ln.amount == 0