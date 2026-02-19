from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class BillTemplateLineBase(BaseModel):
    charge_item_id: int
    is_required: bool = False
    sort_order: int = 0
    note: Optional[str] = None


class BillTemplateLineCreate(BillTemplateLineBase):
    pass


class BillTemplateLineUpdate(BillTemplateLineBase):
    pass


class BillTemplateLineRead(BillTemplateLineBase):
    id: int


class BillTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True
    items: List[BillTemplateLineRead] = []


class BillTemplateCreate(BillTemplateBase):
    items: List[BillTemplateLineCreate] = []


class BillTemplateUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    is_active: Optional[bool]
    items: Optional[List[BillTemplateLineCreate]]


class BillTemplateRead(BillTemplateBase):
    id: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True
