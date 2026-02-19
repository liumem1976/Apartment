from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import require_role, require_any_role
from ..db import engine
from ..models import Bill, BillLine, BillTemplate, BillTemplateLine, ChargeItem
from ..schemas_billing import (
    BillTemplateCreate,
    BillTemplateRead,
    BillTemplateUpdate,
)
from ..billing import compute_billing_cycle


router = APIRouter(prefix="/api/v1/templates", tags=["billing"])


@router.get("/", response_model=List[BillTemplateRead], dependencies=[Depends(require_any_role("clerk", "sales"))])
def list_templates(active: Optional[bool] = None, current_user=Depends(require_any_role("clerk", "sales"))):
    with Session(engine) as session:
        stmt = select(BillTemplate)
        if active is not None:
            stmt = stmt.where(BillTemplate.is_active == active)
        templates = session.exec(stmt).all()
        out = []
        for t in templates:
            lines = session.exec(
                select(BillTemplateLine).where(BillTemplateLine.template_id == t.id).order_by(BillTemplateLine.sort_order)
            ).all()
            items = [
                {
                    "id": ln.id,
                    "charge_item_id": ln.charge_item_id,
                    "is_required": ln.is_required,
                    "sort_order": ln.sort_order,
                    "note": ln.note,
                }
                for ln in lines
            ]
            out.append(
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "is_active": t.is_active,
                    "created_by": t.created_by,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at,
                    "items": items,
                }
            )
        return out


@router.post("/", response_model=BillTemplateRead, dependencies=[Depends(require_role("admin"))])
def create_template(payload: BillTemplateCreate, current_user=Depends(require_role("admin"))):
    with Session(engine) as session:
        t = BillTemplate(
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
            created_by=current_user.id,
        )
        session.add(t)
        session.commit()
        session.refresh(t)

        # add lines
        for it in payload.items:
            line = BillTemplateLine(
                template_id=t.id,
                charge_item_id=it.charge_item_id,
                is_required=it.is_required,
                sort_order=it.sort_order,
                note=it.note,
            )
            session.add(line)
        session.commit()
        # build response dict to avoid detached lazy-loading issues
        lines = session.exec(
            select(BillTemplateLine).where(BillTemplateLine.template_id == t.id).order_by(BillTemplateLine.sort_order)
        ).all()
        items = [
            {
                "id": ln.id,
                "charge_item_id": ln.charge_item_id,
                "is_required": ln.is_required,
                "sort_order": ln.sort_order,
                "note": ln.note,
            }
            for ln in lines
        ]
        return {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "is_active": t.is_active,
            "created_by": t.created_by,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
            "items": items,
        }


@router.get("/{template_id}", response_model=BillTemplateRead)
def get_template(template_id: int):
    with Session(engine) as session:
        t = session.get(BillTemplate, template_id)
        if not t:
            raise HTTPException(status_code=404, detail="template not found")
        lines = session.exec(
            select(BillTemplateLine).where(BillTemplateLine.template_id == t.id).order_by(BillTemplateLine.sort_order)
        ).all()
        items = [
            {
                "id": ln.id,
                "charge_item_id": ln.charge_item_id,
                "is_required": ln.is_required,
                "sort_order": ln.sort_order,
                "note": ln.note,
            }
            for ln in lines
        ]
        return {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "is_active": t.is_active,
            "created_by": t.created_by,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
            "items": items,
        }


@router.put("/{template_id}", response_model=BillTemplateRead, dependencies=[Depends(require_role("admin"))])
def update_template(template_id: int, payload: BillTemplateUpdate, current_user=Depends(require_role("admin"))):
    with Session(engine) as session:
        t = session.get(BillTemplate, template_id)
        if not t:
            raise HTTPException(status_code=404, detail="template not found")
        if payload.name is not None:
            t.name = payload.name
        if payload.description is not None:
            t.description = payload.description
        if payload.is_active is not None:
            t.is_active = payload.is_active
        t.updated_at = None
        session.add(t)
        session.commit()

        # replace items if provided
        if payload.items is not None:
            # delete existing
            existing = session.exec(select(BillTemplateLine).where(BillTemplateLine.template_id == t.id)).all()
            for e in existing:
                session.delete(e)
            session.commit()
            for it in payload.items:
                line = BillTemplateLine(
                    template_id=t.id,
                    charge_item_id=it.charge_item_id,
                    is_required=it.is_required,
                    sort_order=it.sort_order,
                    note=it.note,
                )
                session.add(line)
            session.commit()

        session.refresh(t)
        lines = session.exec(
            select(BillTemplateLine).where(BillTemplateLine.template_id == t.id).order_by(BillTemplateLine.sort_order)
        ).all()
        items = [
            {
                "id": ln.id,
                "charge_item_id": ln.charge_item_id,
                "is_required": ln.is_required,
                "sort_order": ln.sort_order,
                "note": ln.note,
            }
            for ln in lines
        ]
        return {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "is_active": t.is_active,
            "created_by": t.created_by,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
            "items": items,
        }


@router.delete("/{template_id}", dependencies=[Depends(require_role("admin"))])
def delete_template(template_id: int, current_user=Depends(require_role("admin"))):
    with Session(engine) as session:
        t = session.get(BillTemplate, template_id)
        if not t:
            raise HTTPException(status_code=404, detail="template not found")
        # delete lines first
        lines = session.exec(select(BillTemplateLine).where(BillTemplateLine.template_id == t.id)).all()
        for ln in lines:
            session.delete(ln)
        session.delete(t)
        session.commit()
        return {"deleted": True}


class InstantiatePayload:
    unit_id: int
    date: str


@router.post("/{template_id}/instantiate", dependencies=[Depends(require_any_role("clerk", "sales"))])
def instantiate_template(template_id: int, unit_id: int, date: str, current_user=Depends(require_any_role("clerk", "sales"))):
    # create a draft bill for the unit based on template lines (amounts left zero)
    from datetime import datetime

    try:
        d = datetime.strptime(date, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid date")

    with Session(engine) as session:
        t = session.get(BillTemplate, template_id)
        if not t:
            raise HTTPException(status_code=404, detail="template not found")

        # compute cycle
        # find lease start date for unit
        from ..models import Lease, Unit, Building, Community, Company

        lease = session.exec(select(Lease).where(Lease.unit_id == unit_id)).first()
        if not lease:
            raise HTTPException(status_code=400, detail="no lease for unit")
        cycle_start, cycle_end = compute_billing_cycle(lease.start_date, d)

        # ensure not duplicate
        existing = session.exec(select(Bill).where(Bill.unit_id == unit_id, Bill.cycle_start == cycle_start)).first()
        if existing:
            raise HTTPException(status_code=400, detail="bill already exists for cycle")

        # determine company/community via unit->building->community->company
        unit = session.get(Unit, unit_id)
        b = session.get(Building, unit.building_id)
        comm = session.get(Community, b.community_id)
        comp = session.get(Company, comm.company_id)

        bill = Bill(
            company_id=comp.id,
            community_id=comm.id,
            unit_id=unit_id,
            cycle_start=cycle_start,
            cycle_end=cycle_end,
            status="draft",
            total_amount=0,
            template_id=t.id,
        )
        session.add(bill)
        session.flush()

        # copy template lines
        tlines = session.exec(select(BillTemplateLine).where(BillTemplateLine.template_id == t.id).order_by(BillTemplateLine.sort_order)).all()
        for tl in tlines:
            # resolve charge item code
            ci = session.get(ChargeItem, tl.charge_item_id)
            code = ci.code if ci else f"item-{tl.charge_item_id}"
            ln = BillLine(
                bill_id=bill.id,
                item_code=code,
                charge_code=code,
                qty=1,
                unit_price=0,
                amount=0,
            )
            session.add(ln)

        session.commit()
        session.refresh(bill)
        return {"bill_id": bill.id, "status": bill.status}
