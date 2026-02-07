from fastapi import UploadFile
import csv
from io import TextIOWrapper
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any
import json
import traceback

from sqlmodel import Session, select

from .db import engine
from .models import Company, Community, Building, Unit, Tenant, Lease, ImportBatch


class ImportErrors(Exception):
    def __init__(self, errors: List[Dict[str, Any]]):
        self.errors = errors


def _read_csv(upload: UploadFile):
    text = TextIOWrapper(upload.file, encoding="utf-8-sig")
    reader = csv.DictReader(text)
    for i, row in enumerate(reader, start=2):
        yield i, {k.strip(): (v.strip() if v is not None else "") for k, v in row.items()}


def import_rooms_file(upload: UploadFile) -> Dict[str, int]:
    errors: List[Dict[str, Any]] = []
    created = 0
    updated = 0
    with Session(engine) as session:
        try:
            with session.begin():
                for rownum, row in _read_csv(upload):
                    company_code = row.get("company_code")
                    community_code = row.get("community_code")
                    building_code = row.get("building_code")
                    unit_no = row.get("unit_no")
                    remark = row.get("remark") or None

                    if not (company_code and community_code and building_code and unit_no):
                        errors.append({"row": rownum, "error": "missing required field(s)"})
                        continue

                    comp = session.exec(select(Company).where(Company.code == company_code)).first()
                    if not comp:
                        comp = Company(code=company_code, name=company_code)
                        session.add(comp)
                        session.flush()

                    comm = session.exec(select(Community).where(Community.code == community_code, Community.company_id == comp.id)).first()
                    if not comm:
                        comm = Community(company_id=comp.id, code=community_code, name=community_code)
                        session.add(comm)
                        session.flush()

                    b = session.exec(select(Building).where(Building.code == building_code, Building.community_id == comm.id)).first()
                    if not b:
                        b = Building(community_id=comm.id, code=building_code, name=building_code)
                        session.add(b)
                        session.flush()

                    u = session.exec(select(Unit).where(Unit.unit_no == unit_no, Unit.building_id == b.id)).first()
                    if not u:
                        u = Unit(building_id=b.id, unit_no=unit_no, remark=remark)
                        session.add(u)
                        created += 1
                    else:
                        # idempotent update
                        if u.remark != remark:
                            u.remark = remark
                            updated += 1

                if errors:
                    raise ImportErrors(errors)
        finally:
            upload.file.close()

    return {"created": created, "updated": updated}


def import_leases_file(upload: UploadFile) -> Dict[str, int]:
    errors: List[Dict[str, Any]] = []
    created = 0
    updated = 0
    with Session(engine) as session:
        try:
            with session.begin():
                for rownum, row in _read_csv(upload):
                    company_code = row.get("company_code")
                    community_code = row.get("community_code")
                    building_code = row.get("building_code")
                    unit_no = row.get("unit_no")
                    tenant_name = row.get("tenant_name")
                    tenant_mobile = row.get("tenant_mobile")
                    start_date_s = row.get("start_date")
                    end_date_s = row.get("end_date")
                    rent_amount_s = row.get("rent_amount")
                    deposit_amount_s = row.get("deposit_amount")

                    if not (company_code and community_code and building_code and unit_no and tenant_name and start_date_s and end_date_s):
                        errors.append({"row": rownum, "error": "missing required field(s)"})
                        continue

                    # find unit hierarchy
                    comp = session.exec(select(Company).where(Company.code == company_code)).first()
                    if not comp:
                        errors.append({"row": rownum, "error": f"company {company_code} not found"})
                        continue
                    comm = session.exec(select(Community).where(Community.code == community_code, Community.company_id == comp.id)).first()
                    if not comm:
                        errors.append({"row": rownum, "error": f"community {community_code} not found"})
                        continue
                    b = session.exec(select(Building).where(Building.code == building_code, Building.community_id == comm.id)).first()
                    if not b:
                        errors.append({"row": rownum, "error": f"building {building_code} not found"})
                        continue
                    u = session.exec(select(Unit).where(Unit.unit_no == unit_no, Unit.building_id == b.id)).first()
                    if not u:
                        errors.append({"row": rownum, "error": f"unit {unit_no} not found"})
                        continue

                    # parse dates and decimals
                    try:
                        start_date = datetime.strptime(start_date_s, "%Y-%m-%d").date()
                        end_date = datetime.strptime(end_date_s, "%Y-%m-%d").date()
                    except Exception:
                        errors.append({"row": rownum, "error": "invalid date format, expected YYYY-MM-DD"})
                        continue

                    try:
                        rent_amount = Decimal(rent_amount_s) if rent_amount_s else Decimal("0")
                        deposit_amount = Decimal(deposit_amount_s) if deposit_amount_s else Decimal("0")
                    except Exception:
                        errors.append({"row": rownum, "error": "invalid amount format"})
                        continue

                    # check lease overlap for this unit
                    existing_leases = session.exec(select(Lease).where(Lease.unit_id == u.id)).all()
                    overlap = False
                    for el in existing_leases:
                        if (el.start_date <= end_date) and (start_date <= el.end_date):
                            # allow exact same start_date to be treated as idempotent update
                            if el.start_date == start_date:
                                # will update below
                                continue
                            overlap = True
                            break
                    if overlap:
                        errors.append({"row": rownum, "error": "lease date overlaps existing lease"})
                        continue

                    # find or create tenant
                    tenant = session.exec(select(Tenant).where(Tenant.name == tenant_name, Tenant.mobile == tenant_mobile)).first()
                    if not tenant:
                        tenant = Tenant(name=tenant_name, mobile=tenant_mobile)
                        session.add(tenant)
                        session.flush()

                    # idempotent by unit_id + start_date
                    lease = session.exec(select(Lease).where(Lease.unit_id == u.id, Lease.start_date == start_date)).first()
                    if not lease:
                        lease = Lease(unit_id=u.id, tenant_id=tenant.id, start_date=start_date, end_date=end_date, rent_amount=rent_amount, deposit_amount=deposit_amount)
                        session.add(lease)
                        created += 1
                    else:
                        # update fields
                        lease.tenant_id = tenant.id
                        lease.end_date = end_date
                        lease.rent_amount = rent_amount
                        lease.deposit_amount = deposit_amount
                        updated += 1

                if errors:
                    raise ImportErrors(errors)
        finally:
            upload.file.close()

    return {"created": created, "updated": updated}


def _read_csv_from_path(path: str):
    with open(path, "rb") as fh:
        text = TextIOWrapper(fh, encoding="utf-8-sig")
        reader = csv.DictReader(text)
        for i, row in enumerate(reader, start=2):
            yield i, {k.strip(): (v.strip() if v is not None else "") for k, v in row.items()}


def process_rooms_path(path: str) -> Dict[str, int]:
    errors: List[Dict[str, Any]] = []
    created = 0
    updated = 0
    with Session(engine) as session:
        with session.begin():
            for rownum, row in _read_csv_from_path(path):
                company_code = row.get("company_code")
                community_code = row.get("community_code")
                building_code = row.get("building_code")
                unit_no = row.get("unit_no")
                remark = row.get("remark") or None

                if not (company_code and community_code and building_code and unit_no):
                    errors.append({"row": rownum, "error": "missing required field(s)"})
                    continue

                comp = session.exec(select(Company).where(Company.code == company_code)).first()
                if not comp:
                    comp = Company(code=company_code, name=company_code)
                    session.add(comp)
                    session.flush()

                comm = session.exec(select(Community).where(Community.code == community_code, Community.company_id == comp.id)).first()
                if not comm:
                    comm = Community(company_id=comp.id, code=community_code, name=community_code)
                    session.add(comm)
                    session.flush()

                b = session.exec(select(Building).where(Building.code == building_code, Building.community_id == comm.id)).first()
                if not b:
                    b = Building(community_id=comm.id, code=building_code, name=building_code)
                    session.add(b)
                    session.flush()

                u = session.exec(select(Unit).where(Unit.unit_no == unit_no, Unit.building_id == b.id)).first()
                if not u:
                    u = Unit(building_id=b.id, unit_no=unit_no, remark=remark)
                    session.add(u)
                    created += 1
                else:
                    if u.remark != remark:
                        u.remark = remark
                        updated += 1

            if errors:
                raise ImportErrors(errors)

    return {"created": created, "updated": updated}


def process_leases_path(path: str) -> Dict[str, int]:
    errors: List[Dict[str, Any]] = []
    created = 0
    updated = 0
    with Session(engine) as session:
        with session.begin():
            for rownum, row in _read_csv_from_path(path):
                company_code = row.get("company_code")
                community_code = row.get("community_code")
                building_code = row.get("building_code")
                unit_no = row.get("unit_no")
                tenant_name = row.get("tenant_name")
                tenant_mobile = row.get("tenant_mobile")
                start_date_s = row.get("start_date")
                end_date_s = row.get("end_date")
                rent_amount_s = row.get("rent_amount")
                deposit_amount_s = row.get("deposit_amount")

                if not (company_code and community_code and building_code and unit_no and tenant_name and start_date_s and end_date_s):
                    errors.append({"row": rownum, "error": "missing required field(s)"})
                    continue

                comp = session.exec(select(Company).where(Company.code == company_code)).first()
                if not comp:
                    errors.append({"row": rownum, "error": f"company {company_code} not found"})
                    continue
                comm = session.exec(select(Community).where(Community.code == community_code, Community.company_id == comp.id)).first()
                if not comm:
                    errors.append({"row": rownum, "error": f"community {community_code} not found"})
                    continue
                b = session.exec(select(Building).where(Building.code == building_code, Building.community_id == comm.id)).first()
                if not b:
                    errors.append({"row": rownum, "error": f"building {building_code} not found"})
                    continue
                u = session.exec(select(Unit).where(Unit.unit_no == unit_no, Unit.building_id == b.id)).first()
                if not u:
                    errors.append({"row": rownum, "error": f"unit {unit_no} not found"})
                    continue

                try:
                    start_date = datetime.strptime(start_date_s, "%Y-%m-%d").date()
                    end_date = datetime.strptime(end_date_s, "%Y-%m-%d").date()
                except Exception:
                    errors.append({"row": rownum, "error": "invalid date format, expected YYYY-MM-DD"})
                    continue

                try:
                    rent_amount = Decimal(rent_amount_s) if rent_amount_s else Decimal("0")
                    deposit_amount = Decimal(deposit_amount_s) if deposit_amount_s else Decimal("0")
                except Exception:
                    errors.append({"row": rownum, "error": "invalid amount format"})
                    continue

                existing_leases = session.exec(select(Lease).where(Lease.unit_id == u.id)).all()
                overlap = False
                for el in existing_leases:
                    if (el.start_date <= end_date) and (start_date <= el.end_date):
                        if el.start_date == start_date:
                            continue
                        overlap = True
                        break
                if overlap:
                    errors.append({"row": rownum, "error": "lease date overlaps existing lease"})
                    continue

                tenant = session.exec(select(Tenant).where(Tenant.name == tenant_name, Tenant.mobile == tenant_mobile)).first()
                if not tenant:
                    tenant = Tenant(name=tenant_name, mobile=tenant_mobile)
                    session.add(tenant)
                    session.flush()

                lease = session.exec(select(Lease).where(Lease.unit_id == u.id, Lease.start_date == start_date)).first()
                if not lease:
                    lease = Lease(unit_id=u.id, tenant_id=tenant.id, start_date=start_date, end_date=end_date, rent_amount=rent_amount, deposit_amount=deposit_amount)
                    session.add(lease)
                    created += 1
                else:
                    lease.tenant_id = tenant.id
                    lease.end_date = end_date
                    lease.rent_amount = rent_amount
                    lease.deposit_amount = deposit_amount
                    updated += 1

            if errors:
                raise ImportErrors(errors)

    return {"created": created, "updated": updated}


def process_import_batch(batch_id: int, path: str):
    # update batch status and run import, capturing results/errors
    with Session(engine) as session:
        b0 = session.get(ImportBatch, batch_id)
        if not b0:
            return
        kind = b0.kind
        b0.status = "processing"
        b0.started_at = datetime.utcnow()
        session.add(b0)
        session.commit()

    try:
        if kind == "rooms":
            res = process_rooms_path(path)
        else:
            res = process_leases_path(path)
        # ensure result is JSON-serializable
        try:
            result_json = json.dumps(res, ensure_ascii=False)
        except Exception:
            # fallback to string representation
            result_json = json.dumps({"result": str(res)}, ensure_ascii=False)
        with Session(engine) as session:
            b = session.get(ImportBatch, batch_id)
            b.status = "done"
            b.finished_at = datetime.utcnow()
            b.result = result_json
            session.add(b)
            session.commit()
    except ImportErrors as ie:
        with Session(engine) as session:
            b = session.get(ImportBatch, batch_id)
            b.status = "failed"
            b.finished_at = datetime.utcnow()
            b.errors = json.dumps(ie.errors, ensure_ascii=False)
            session.add(b)
            session.commit()
    except Exception as e:
        tb = traceback.format_exc()
        with Session(engine) as session:
            b = session.get(ImportBatch, batch_id)
            b.status = "failed"
            b.finished_at = datetime.utcnow()
            b.errors = json.dumps({"error": str(e), "trace": tb}, ensure_ascii=False)
            session.add(b)
            session.commit()
