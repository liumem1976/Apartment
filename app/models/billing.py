from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import relationship as sa_relationship
from sqlmodel import Field, Relationship, SQLModel


class BillTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, index=True)
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    created_by: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    items: List["BillTemplateLine"] = Relationship(
        back_populates="template",
        sa_relationship=sa_relationship("BillTemplateLine", back_populates="template"),
    )


class BillTemplateLine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="billtemplate.id")
    charge_item_id: int = Field(foreign_key="chargeitem.id")
    is_required: bool = Field(default=False)
    sort_order: int = Field(default=0)
    note: Optional[str] = None

    template: Optional[BillTemplate] = Relationship(
        back_populates="items",
        sa_relationship=sa_relationship("BillTemplate", back_populates="items"),
    )
