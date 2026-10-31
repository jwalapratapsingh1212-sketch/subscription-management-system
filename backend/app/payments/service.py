"""Business logic for idempotent payment recording and invoice balance reconciliation."""
from datetime import date, datetime, timezone
from decimal import Decimal
import secrets
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.core.financials import quantize_money
from app.core.permissions import enforce_customer_ownership, get_customer_for_user
from app.invoices.service import sync_invoice_overdue_state
from app.models import Invoice, Payment, User
from app.payments.schemas import (
    InvoiceBalanceResponse,
    PaymentCreateRequest,
    PaymentResponse,
)


def _next_payment_number(db: Session) -> str:
    count = db.query(Payment).count() + 1
    year = date.today().year
    candidate = f"PAY-{year}-{count:04d}"
    while db.query(Payment).filter(Payment.payment_number == candidate).first() is not None:
        count += 1
        candidate = f"PAY-{year}-{count:04d}"
    return candidate


def format_payment_response(payment: Payment) -> PaymentResponse:
    inv = payment.invoice
    return PaymentResponse(
        id=payment.id,
        payment_number=payment.payment_number,
        invoice_id=payment.invoice_id,
        invoice_number=inv.invoice_number if inv else None,
        customer_id=payment.customer_id,
        customer_name=payment.customer.name if payment.customer else None,
        method=payment.method,
        amount=payment.amount,
        payment_date=payment.payment_date,
        reference=payment.reference,
        note=payment.note,
        idempotency_key=payment.idempotency_key,
        status=payment.status,
        invoice_state=inv.state if inv else None,
        invoice_payment_status=inv.payment_status if inv else None,
        invoice_amount_due=inv.amount_due if inv else None,
        created_at=payment.created_at,
    )


def reconcile_invoice_balance(db: Session, invoice: Invoice) -> None:
    """Recalculate invoice paid/outstanding amounts and update invoice & subscription states."""
    succeeded_payments = (
        db.query(Payment)
        .filter(Payment.invoice_id == invoice.id, Payment.status == "succeeded")
        .all()
    )
    total_paid = quantize_money(
        sum((p.amount for p in succeeded_payments), Decimal("0.00"))
    )
    remaining = quantize_money(max(Decimal("0.00"), invoice.total - total_paid))

    invoice.amount_paid = total_paid
    invoice.amount_due = remaining

    if remaining == Decimal("0.00") and invoice.state == "confirmed":
        invoice.state = "paid"
        invoice.payment_status = "paid"
        invoice.paid_at = datetime.now(timezone.utc)
    else:
        sync_invoice_overdue_state(db, invoice)

    # If subscription was past_due, check if all overdue invoices for this subscription are now resolved
    sub = invoice.subscription
    if sub and sub.state == "past_due":
        today = date.today()
        remaining_overdue = (
            db.query(Invoice)
            .filter(
                Invoice.subscription_id == sub.id,
                Invoice.state == "confirmed",
                Invoice.amount_due > Decimal("0.00"),
                Invoice.due_date < today,
            )
            .count()
        )
        if remaining_overdue == 0:
            sub.state = "active"


def record_payment(
    db: Session,
    payload: PaymentCreateRequest,
    current_user: User,
    header_idempotency_key: Optional[str] = None,
) -> PaymentResponse:
    """Record a payment against an invoice with strict idempotency and overpayment protection."""
    idem_key = (
        payload.idempotency_key
        or header_idempotency_key
        or f"idem-{secrets.token_hex(12)}"
    ).strip()

    # Check idempotency key first
    existing_payment = (
        db.query(Payment).filter(Payment.idempotency_key == idem_key).first()
    )
    if existing_payment:
        enforce_customer_ownership(db, current_user, existing_payment.customer_id)
        req_amount = quantize_money(payload.amount)
        if (
            existing_payment.invoice_id != payload.invoice_id
            or existing_payment.amount != req_amount
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key has already been used with different payment parameters.",
            )
        return format_payment_response(existing_payment)

    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == payload.invoice_id)
        .with_for_update()
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")

    enforce_customer_ownership(db, current_user, invoice.customer_id)

    if invoice.state == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record a payment against a cancelled invoice.",
        )
    if invoice.state == "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice must be confirmed before recording a payment.",
        )
    if invoice.state == "paid" or invoice.amount_due <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already paid in full.",
        )

    pay_amount = quantize_money(payload.amount)
    if pay_amount > invoice.amount_due:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Payment amount (${pay_amount:.2f}) exceeds the invoice outstanding balance "
                f"(${invoice.amount_due:.2f}). Overpayments are rejected."
            ),
        )

    pay_dt = payload.payment_date or date.today()
    pay_number = _next_payment_number(db)

    payment = Payment(
        payment_number=pay_number,
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        method=payload.method,
        amount=pay_amount,
        payment_date=pay_dt,
        reference=payload.reference or f"REF-{secrets.token_hex(4).upper()}",
        note=payload.note,
        idempotency_key=idem_key,
        status="succeeded",
        recorded_by_id=current_user.id,
    )
    db.add(payment)
    db.flush()

    reconcile_invoice_balance(db, invoice)

    log_audit_event(
        db,
        action="payment.record",
        entity_type="payment",
        entity_id=payment.id,
        actor=current_user,
        metadata={
            "payment_number": payment.payment_number,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "amount": str(payment.amount),
            "remaining_due": str(invoice.amount_due),
            "new_invoice_state": invoice.state,
        },
    )
    db.commit()
    db.refresh(payment)
    return format_payment_response(payment)


def list_payments(
    db: Session,
    current_user: User,
    invoice_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    method: Optional[str] = None,
) -> List[PaymentResponse]:
    query = db.query(Payment)
    if current_user.role == "customer":
        own_customer = get_customer_for_user(db, current_user)
        if not own_customer:
            return []
        query = query.filter(Payment.customer_id == own_customer.id)
    elif customer_id is not None:
        query = query.filter(Payment.customer_id == customer_id)

    if invoice_id is not None:
        query = query.filter(Payment.invoice_id == invoice_id)
    if method:
        query = query.filter(Payment.method == method)

    rows = query.order_by(Payment.id.desc()).all()
    return [format_payment_response(p) for p in rows]


def get_invoice_balance(
    db: Session, invoice_id: int, current_user: User
) -> InvoiceBalanceResponse:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    enforce_customer_ownership(db, current_user, invoice.customer_id)

    if sync_invoice_overdue_state(db, invoice):
        db.commit()
        db.refresh(invoice)

    is_overdue = (
        invoice.state == "confirmed"
        and invoice.amount_due > Decimal("0.00")
        and invoice.due_date < date.today()
    )
    return InvoiceBalanceResponse(
        invoice_id=invoice.id,
        invoice_number=invoice.invoice_number,
        state=invoice.state,
        payment_status=invoice.payment_status,
        is_overdue=is_overdue,
        due_date=invoice.due_date,
        total=invoice.total,
        amount_paid=invoice.amount_paid,
        amount_due=invoice.amount_due,
        payments=[format_payment_response(p) for p in invoice.payments],
    )

