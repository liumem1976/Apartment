from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    bill_id: Optional[int] = Field(None, description="Target bill id (optional)")
    unit_id: Optional[int] = Field(None, description="Target unit id (optional)")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    method: Optional[str] = Field(None, description="Payment method")
    reference: Optional[str] = Field(None, description="External reference")


class PaymentResponse(BaseModel):
    payment_id: int
    created_at: Optional[datetime] = None
