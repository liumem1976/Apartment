from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from sqlmodel import Session, select
import os

from .db import init_db, engine
from .models import User
from .auth import (
    create_access_token,
    authenticate_user,
    get_password_hash,
    get_current_user,
    require_role,
)
from .billing import generate_bill_for_unit, generate_batch_for_company
from datetime import datetime
import json
from sqlmodel import Session, select
from .models import Bill, BillLine, AuditLog
from fastapi import File, UploadFile, BackgroundTasks
from .imports import import_rooms_file, import_leases_file, ImportErrors, process_import_batch
import shutil
import uuid
import os
from .models import ImportBatch

app = FastAPI(title="LAN Apartment Billing System")

# Strict CORS configuration placeholder; set via env `CORS_ALLOWED`
allowed = os.getenv("CORS_ALLOWED", "").split(",") if os.getenv("CORS_ALLOWED") else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    # Ensure default admin exists for initial setup (password from env only)
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pwd = os.getenv("ADMIN_PASSWORD")
    if admin_pwd:
        with Session(engine) as session:
            existing = session.exec(select(User).where(User.username == admin_user)).first()
            if not existing:
                u = User(username=admin_user, password_hash=get_password_hash(admin_pwd), role="admin")
                session.add(u)
                session.commit()


@app.get("/", response_class=HTMLResponse)
def index():
    return "<h1>LAN Apartment Billing System</h1><p>Service up.</p>"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/users/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role}


@app.post("/api/users", dependencies=[Depends(require_role("admin"))])
def create_user(username: str, password: str, role: str = "clerk"):
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == username)).first()
        if existing:
            raise HTTPException(status_code=400, detail="User exists")
        user = User(username=username, password_hash=get_password_hash(password), role=role)
        session.add(user)
        session.commit()
        return {"username": user.username, "role": user.role}


@app.post("/api/v1/bills/generate")
def api_generate_bill(unit_id: int, date: str, current_user: User = Depends(require_role("clerk"))):
    d = datetime.strptime(date, "%Y-%m-%d").date()
    bill = generate_bill_for_unit(unit_id, d, actor_id=current_user.id)
    return {"bill_id": bill.id, "cycle_start": str(bill.cycle_start), "cycle_end": str(bill.cycle_end)}


@app.post("/api/v1/bills/generate-batch")
def api_generate_batch(company_id: int, date: str, current_user: User = Depends(require_role("clerk"))):
    d = datetime.strptime(date, "%Y-%m-%d").date()
    bills = generate_batch_for_company(company_id, d, actor_id=current_user.id)
    return {"created": len(bills)}


def _record_audit(session: Session, actor_id: int, action: str, before: Optional[str], after: Optional[str], ip: Optional[str] = None):
    al = AuditLog(actor_id=actor_id, action=action, before=before, after=after, ip=ip)
    session.add(al)


@app.post("/api/v1/bills/{bill_id}/submit")
def api_bill_submit(bill_id: int, current_user: User = Depends(require_role("clerk"))):
    with Session(engine) as session:
        bill = session.get(Bill, bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        if bill.status != "draft":
            raise HTTPException(status_code=400, detail="Bill not in draft")
        before = json.dumps({"status": bill.status})
        bill.status = "submitted"
        _record_audit(session, current_user.id, "submit", before, json.dumps({"status": bill.status}))
        session.add(bill)
        session.commit()
        return {"bill_id": bill.id, "status": bill.status}


@app.post("/api/v1/bills/{bill_id}/approve")
def api_bill_approve(bill_id: int, current_user: User = Depends(require_role("finance"))):
    with Session(engine) as session:
        bill = session.get(Bill, bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        if bill.status != "submitted":
            raise HTTPException(status_code=400, detail="Bill not in submitted state")
        # freeze snapshot of lines
        lines = session.exec(select(BillLine).where(BillLine.bill_id == bill.id)).all()
        snapshot = []
        for l in lines:
            snapshot.append({"charge_code": l.charge_code, "qty": str(l.qty) if l.qty is not None else None, "unit_price": str(l.unit_price) if l.unit_price is not None else None, "amount": str(l.amount)})
        before = json.dumps({"status": bill.status})
        bill.frozen_snapshot = json.dumps(snapshot, ensure_ascii=False)
        bill.status = "approved"
        _record_audit(session, current_user.id, "approve", before, json.dumps({"status": bill.status}))
        session.add(bill)
        session.commit()
        return {"bill_id": bill.id, "status": bill.status}


@app.post("/api/v1/bills/{bill_id}/issue")
def api_bill_issue(bill_id: int, current_user: User = Depends(require_role("finance"))):
    with Session(engine) as session:
        bill = session.get(Bill, bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        if bill.status != "approved":
            raise HTTPException(status_code=400, detail="Bill not in approved state")
        before = json.dumps({"status": bill.status})
        bill.status = "issued"
        _record_audit(session, current_user.id, "issue", before, json.dumps({"status": bill.status}))
        session.add(bill)
        session.commit()
        return {"bill_id": bill.id, "status": bill.status}


@app.post("/api/v1/bills/{bill_id}/void")
def api_bill_void(bill_id: int, current_user: User = Depends(require_role("admin"))):
    with Session(engine) as session:
        bill = session.get(Bill, bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        before = json.dumps({"status": bill.status})
        bill.status = "void"
        _record_audit(session, current_user.id, "void", before, json.dumps({"status": bill.status}))
        session.add(bill)
        session.commit()
        return {"bill_id": bill.id, "status": bill.status}

@app.post("/api/v1/imports/rooms", dependencies=[Depends(require_role("clerk"))])
def api_import_rooms(file: UploadFile = File(...), background_tasks: BackgroundTasks = None, current_user: User = Depends(require_role("clerk"))):
    # persist upload and create ImportBatch, then schedule background processing
    os.makedirs("./data/imports", exist_ok=True)
    filename = file.filename or f"rooms-{uuid.uuid4().hex}.csv"
    with Session(engine) as session:
        batch = ImportBatch(filename=filename, kind="rooms", status="pending")
        session.add(batch)
        session.commit()
        session.refresh(batch)

    dest_path = os.path.join("./data/imports", f"{batch.id}_{filename}")
    with open(dest_path, "wb") as out_f:
        shutil.copyfileobj(file.file, out_f)
    file.file.close()

    # schedule background processing
    background_tasks.add_task(process_import_batch, batch.id, dest_path)
    return {"batch_id": batch.id}


@app.post("/api/v1/imports/leases", dependencies=[Depends(require_role("clerk"))])
def api_import_leases(file: UploadFile = File(...), background_tasks: BackgroundTasks = None, current_user: User = Depends(require_role("clerk"))):
    os.makedirs("./data/imports", exist_ok=True)
    filename = file.filename or f"leases-{uuid.uuid4().hex}.csv"
    with Session(engine) as session:
        batch = ImportBatch(filename=filename, kind="leases", status="pending")
        session.add(batch)
        session.commit()
        session.refresh(batch)

    dest_path = os.path.join("./data/imports", f"{batch.id}_{filename}")
    with open(dest_path, "wb") as out_f:
        shutil.copyfileobj(file.file, out_f)
    file.file.close()

    background_tasks.add_task(process_import_batch, batch.id, dest_path)
    return {"batch_id": batch.id}


@app.get("/api/v1/imports/batches/{batch_id}", dependencies=[Depends(require_role("clerk"))])
def api_get_import_batch(batch_id: int, current_user: User = Depends(require_role("clerk"))):
    with Session(engine) as session:
        b = session.get(ImportBatch, batch_id)
        if not b:
            raise HTTPException(status_code=404, detail="batch not found")
        return {
            "id": b.id,
            "filename": b.filename,
            "kind": b.kind,
            "status": b.status,
            "created_at": str(b.created_at) if b.created_at else None,
            "started_at": str(b.started_at) if b.started_at else None,
            "finished_at": str(b.finished_at) if b.finished_at else None,
            "result": json.loads(b.result) if b.result else None,
            "errors": json.loads(b.errors) if b.errors else None,
        }

