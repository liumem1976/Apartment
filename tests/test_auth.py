from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth import get_password_hash
from app.db import engine, init_db
from app.main import app
from app.models import User


def setup_module(module):
    init_db()


def test_create_and_login_user():
    client = TestClient(app)
    # insert user directly
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == "tuser")).first()
        if not existing:
            user = User(
                username="tuser",
                password_hash=get_password_hash("testpass"),
                role="clerk",
            )
            session.add(user)
            session.commit()

    # login
    r = client.post(
        "/api/auth/token", data={"username": "tuser", "password": "testpass"}
    )
    assert r.status_code == 200
    j = r.json()
    assert "access_token" in j


def test_generate_bill_requires_auth():
    client = TestClient(app)
    # call generate without token
    r = client.post(
        "/api/v1/bills/generate", params={"unit_id": 1, "date": "2026-02-15"}
    )
    assert r.status_code in (401, 403)


def test_cookie_login_logout_and_dashboard_rbac():
    client = TestClient(app)
    # ensure DB initialized
    # create a clerk user
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == "testclerk")).first()
        if not existing:
            u = User(username="testclerk", password_hash=get_password_hash("s3cret"), role="clerk")
            session.add(u)
            session.commit()

    # login via HTML form
    r = client.post("/login", data={"username": "testclerk", "password": "s3cret"})
    assert r.status_code in (200, 303, 307)

    # dashboard should be accessible
    r2 = client.get("/dashboard")
    assert r2.status_code == 200
    assert "testclerk" in r2.text

    # logout
    r3 = client.get("/logout")
    assert r3.status_code in (200, 303, 307)

    # dashboard now requires auth
    r4 = client.get("/dashboard")
    assert r4.status_code == 401


def test_cookie_login_failed():
    client = TestClient(app)
    # ensure user
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == "failuser")).first()
        if not existing:
            u = User(username="failuser", password_hash=get_password_hash("goodpw"), role="clerk")
            session.add(u)
            session.commit()

    r = client.post("/login", data={"username": "failuser", "password": "badpw"}, follow_redirects=False)
    assert r.status_code in (303, 307)
    # no session cookie set
    assert "ap_session" not in client.cookies
