"""Pydantic schemas for payment recording, idempotency, and invoice balance reconciliation."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreateRequest(BaseModel):
    invoice_id: int
    method: str = Field(
        default="credit_card",
        pattern="^(credit_card|bank_transfer|upi|wire|cash|check)$",
    )
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    payment_date: Optional[date] = None
    reference: Optional[str] = Field(default=None, max_length=128)
    note: Optional[str] = None
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Unique key to prevent duplicate payment processing on retries",
    )


class PaymentResponse(BaseModel):
    id: int
    payment_number: str
    invoice_id: int
    invoice_number: Optional[str] = None
    customer_id: int
    customer_name: Optional[str] = None
    method: str
    amount: Decimal
    payment_date: date
    reference: Optional[str] = None
    note: Optional[str] = None
    idempotency_key: str
    status: str
    invoice_state: Optional[str] = None
    invoice_payment_status: Optional[str] = None
    invoice_amount_due: Optional[Decimal] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceBalanceResponse(BaseModel):
    invoice_id: int
    invoice_number: str
    state: str
    payment_status: str
    is_overdue: bool
    due_date: date
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    payments: List[PaymentResponse] = Field(default_factory=list)

