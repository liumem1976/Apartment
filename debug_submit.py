from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth import get_password_hash
from app.db import engine
from app.main import app
from app.models import Unit, User

client = TestClient(app)
with Session(engine) as s:
    u = s.exec(select(User).where(User.username == "clerk1")).first()
    if not u:
        s.add(
            User(
                username="clerk1",
                password_hash=get_password_hash("cpass"),
                role="clerk",
            )
        )
        s.commit()

res = client.post("/api/auth/token", data={"username": "clerk1", "password": "cpass"})
print("token", res.status_code, res.text)
token = res.json().get("access_token")

with Session(engine) as s:
    unit = s.exec(select(Unit)).first()
    if not unit:
        print("no unit found")
        raise SystemExit(1)
    uid = unit.id

res = client.post(
    "/api/v1/bills/generate",
    params={"unit_id": uid, "date": "2026-02-15"},
    headers={"Authorization": f"Bearer {token}"},
)
print("generate", res.status_code, res.text)
if res.status_code == 200:
    bid = res.json()["bill_id"]
    res2 = client.post(
        f"/api/v1/bills/{bid}/submit", headers={"Authorization": f"Bearer {token}"}
    )
    print("submit", res2.status_code, res2.text)
