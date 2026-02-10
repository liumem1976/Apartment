from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth import get_password_hash
from app.db import engine, init_db
from app.main import app
from app.models import Lease, Unit, User


def setup_module(module):
    init_db()


def make_user(username, password, role):
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == username)).first()
        if existing:
            return existing
        u = User(
            username=username, password_hash=get_password_hash(password), role=role
        )
        session.add(u)
        session.commit()
        return u


def test_rooms_import_idempotent():
    client = TestClient(app)
    make_user("clerkx", "pass", "clerk")
    r = client.post("/api/auth/token", data={"username": "clerkx", "password": "pass"})
    token = r.json()["access_token"]
    csv_content = "company_code,community_code,building_code,unit_no,remark\nTESTR,CMR,BR,101,first\nTESTR,CMR,BR,102,second\n"
    # cleanup any previous test data with same codes to ensure deterministic behavior
    from sqlalchemy import delete

    from app.models import Bill, BillLine, Building, Community, Company, Unit

    with Session(engine) as s:
        comp = s.exec(select(Company).where(Company.code == "TESTR")).first()
        if comp:
            # delete dependent units and buildings
            comms = s.exec(
                select(Community).where(Community.company_id == comp.id)
            ).all()
            for comm in comms:
                blds = s.exec(
                    select(Building).where(Building.community_id == comm.id)
                ).all()
                for bld in blds:
                    units = s.exec(select(Unit).where(Unit.building_id == bld.id)).all()
                    for u in units:
                        s.exec(
                            delete(BillLine).where(
                                BillLine.bill_id.in_(
                                    select(Bill.id).where(Bill.unit_id == u.id)
                                )
                            )
                        )
                        s.exec(delete(Bill).where(Bill.unit_id == u.id))
                    s.exec(delete(Unit).where(Unit.building_id == bld.id))
                s.exec(delete(Building).where(Building.community_id == comm.id))
            s.exec(delete(Community).where(Community.company_id == comp.id))
            s.exec(delete(Company).where(Company.id == comp.id))
            s.commit()
    files = {"file": ("rooms.csv", csv_content, "text/csv")}
    res = client.post(
        "/api/v1/imports/rooms",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    # support new async-batch response returning batch_id
    if body.get("created") is None and body.get("batch_id"):
        batch_id = body.get("batch_id")
        # poll batch status
        import time

        for _ in range(20):
            r2 = client.get(
                f"/api/v1/imports/batches/{batch_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r2.status_code == 200
            b = r2.json()
            if b.get("status") in ("done", "failed"):
                break
            time.sleep(0.05)
        assert b.get("result") is not None
        assert b.get("result").get("created") == 2
    else:
        assert body.get("created") == 2

    # import again -> idempotent (created 0)
    res2 = client.post(
        "/api/v1/imports/rooms",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    body2 = res2.json()
    if body2.get("created") is None and body2.get("batch_id"):
        batch_id = body2.get("batch_id")
        import time

        for _ in range(20):
            r3 = client.get(
                f"/api/v1/imports/batches/{batch_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r3.status_code == 200
            b2 = r3.json()
            if b2.get("status") in ("done", "failed"):
                break
            time.sleep(0.05)
        assert b2.get("result").get("created") == 0
    else:
        assert body2.get("created") == 0


def test_leases_import_rollback_on_overlap():
    client = TestClient(app)
    make_user("clerkl", "pass", "clerk")
    r = client.post("/api/auth/token", data={"username": "clerkl", "password": "pass"})
    token = r.json()["access_token"]

    # create a fresh test unit (rooms import)
    csv_rooms = "company_code,community_code,building_code,unit_no,remark\nTESTL,CM1,BL,201,foo\n"
    files_rooms = {"file": ("rooms.csv", csv_rooms, "text/csv")}
    r = client.post(
        "/api/v1/imports/rooms",
        files=files_rooms,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    # find the created unit
    with Session(engine) as s:
        unit = s.exec(select(Unit).where(Unit.unit_no == "201")).first()
        if not unit:
            raise AssertionError("no unit to attach lease to; rooms import failed")
        uid = unit.id

    # create an existing lease that overlaps
    from app.models import Tenant

    with Session(engine) as s:
        existing = s.exec(select(Lease).where(Lease.unit_id == uid)).first()
        if not existing:
            t = Tenant(name="Existing", mobile="13900000000")
            s.add(t)
            s.flush()
            lease = Lease(
                unit_id=uid,
                tenant_id=t.id,
                start_date=date(2026, 2, 1),
                end_date=date(2026, 2, 28),
                rent_amount=1000,
                deposit_amount=1000,
            )
            s.add(lease)
            s.commit()

    # attempt import with overlapping lease row
    csv_content = "company_code,community_code,building_code,unit_no,tenant_name,tenant_mobile,start_date,end_date,rent_amount,deposit_amount\nTESTL,CM1,BL,201,John,13800000000,2026-02-15,2026-03-14,1200,500\n"
    files = {"file": ("leases.csv", csv_content, "text/csv")}
    res = client.post(
        "/api/v1/imports/leases",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    if body.get("errors") is None and body.get("batch_id"):
        batch_id = body.get("batch_id")
        import time

        for _ in range(20):
            r2 = client.get(
                f"/api/v1/imports/batches/{batch_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r2.status_code == 200
            b = r2.json()
            if b.get("status") in ("done", "failed"):
                break
            time.sleep(0.05)
        # should have errors recorded
        assert b.get("errors") is not None
    else:
        assert "errors" in body
