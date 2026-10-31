"""HTTP endpoints for payment recording and invoice balance reconciliation."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models import User
from app.payments.schemas import (
    InvoiceBalanceResponse,
    PaymentCreateRequest,
    PaymentResponse,
)
from app.payments.service import get_invoice_balance, list_payments, record_payment

payments_router = APIRouter(prefix="/payments", tags=["Payments & Reconciliation"])
invoice_balance_router = APIRouter(prefix="/invoices", tags=["Payments & Reconciliation"])


@payments_router.get("", response_model=List[PaymentResponse])
def get_payments_list(
    invoice_id: Optional[int] = Query(default=None),
    customer_id: Optional[int] = Query(default=None),
    method: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recorded payments (scoped to own records for Customer role)."""
    return list_payments(
        db,
        current_user=current_user,
        invoice_id=invoice_id,
        customer_id=customer_id,
        method=method,
    )


@payments_router.post(
    "", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED
)
def post_payment(
    payload: PaymentCreateRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record an invoice payment with idempotency and automatic balance reconciliation."""
    return record_payment(
        db,
        payload=payload,
        current_user=current_user,
        header_idempotency_key=idempotency_key,
    )


@invoice_balance_router.get("/{invoice_id}/balance", response_model=InvoiceBalanceResponse)
def get_invoice_balance_endpoint(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve reconciled balance and payment allocations for an invoice."""
    return get_invoice_balance(db, invoice_id, current_user)

