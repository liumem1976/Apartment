import os
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.main import app
from app.db import init_db, engine
from app.models import User
from app.auth import get_password_hash


def setup_module(module):
    init_db()


def test_create_and_login_user():
    client = TestClient(app)
    # insert user directly
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == "tuser")).first()
        if not existing:
            user = User(username="tuser", password_hash=get_password_hash("testpass"), role="clerk")
            session.add(user)
            session.commit()

    # login
    r = client.post("/api/auth/token", data={"username": "tuser", "password": "testpass"})
    assert r.status_code == 200
    j = r.json()
    assert "access_token" in j


def test_generate_bill_requires_auth():
    client = TestClient(app)
    # call generate without token
    r = client.post("/api/v1/bills/generate", params={"unit_id": 1, "date": "2026-02-15"})
    assert r.status_code in (401, 403)
