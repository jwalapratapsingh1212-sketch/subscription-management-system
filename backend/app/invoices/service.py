"""Business logic for tax rules, discounts, automated billing engine, and invoice lifecycle."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import secrets
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.core.financials import (
    calculate_order_totals,
    compute_billing_period,
    quantize_money,
)
from app.core.permissions import enforce_customer_ownership, get_customer_for_user
from app.invoices.schemas import (
    BillingRunSummaryResponse,
    DiscountCreateRequest,
    DiscountUpdateRequest,
    InvoiceGenerateRequest,
    InvoiceLineResponse,
    InvoiceResponse,
    TaxRuleCreateRequest,
    TaxRuleUpdateRequest,
)
from app.models import (
    BillingJob,
    Discount,
    Invoice,
    InvoiceLine,
    Subscription,
    TaxRule,
    User,
)


def _next_invoice_number(db: Session) -> str:
    count = db.query(Invoice).count() + 1
    year = date.today().year
    candidate = f"INV-{year}-{count:04d}"
    while db.query(Invoice).filter(Invoice.invoice_number == candidate).first() is not None:
        count += 1
        candidate = f"INV-{year}-{count:04d}"
    return candidate


def sync_invoice_overdue_state(db: Session, invoice: Invoice, today: Optional[date] = None) -> bool:
    """Update payment_status to 'overdue' (and subscription to 'past_due') if past due_date with remaining balance."""
    ref_today = today or date.today()
    changed = False
    if invoice.state == "cancelled":
        if invoice.payment_status != "cancelled":
            invoice.payment_status = "cancelled"
            changed = True
        return changed

    if invoice.amount_due <= Decimal("0.00") and invoice.state == "confirmed":
        invoice.state = "paid"
        invoice.payment_status = "paid"
        if not invoice.paid_at:
            invoice.paid_at = datetime.now(timezone.utc)
        changed = True
    elif invoice.state == "paid":
        if invoice.payment_status != "paid":
            invoice.payment_status = "paid"
            changed = True
    elif invoice.state == "confirmed" and invoice.amount_due > Decimal("0.00"):
        if invoice.due_date < ref_today:
            if invoice.payment_status != "overdue":
                invoice.payment_status = "overdue"
                changed = True
            if invoice.subscription and invoice.subscription.state == "active":
                invoice.subscription.state = "past_due"
                changed = True
        else:
            expected_status = (
                "partially_paid"
                if invoice.amount_paid > Decimal("0.00")
                else "unpaid"
            )
            if invoice.payment_status != expected_status:
                invoice.payment_status = expected_status
                changed = True
    return changed


def format_invoice_response(db: Session, invoice: Invoice) -> InvoiceResponse:
    if sync_invoice_overdue_state(db, invoice):
        db.commit()
        db.refresh(invoice)

    today = date.today()
    is_overdue = (
        invoice.state == "confirmed"
        and invoice.amount_due > Decimal("0.00")
        and invoice.due_date < today
    )
    return InvoiceResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        subscription_id=invoice.subscription_id,
        subscription_number=invoice.subscription.subscription_number if invoice.subscription else None,
        customer_id=invoice.customer_id,
        customer_name=invoice.customer.name if invoice.customer else None,
        customer_email=invoice.customer.email if invoice.customer else None,
        customer_address=invoice.customer.billing_address if invoice.customer else None,
        discount_id=invoice.discount_id,
        billing_period_start=invoice.billing_period_start,
        billing_period_end=invoice.billing_period_end,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        state=invoice.state,
        payment_status=invoice.payment_status,
        is_overdue=is_overdue,
        subtotal=invoice.subtotal,
        discount_amount=invoice.discount_amount,
        tax_amount=invoice.tax_amount,
        total=invoice.total,
        amount_paid=invoice.amount_paid,
        amount_due=invoice.amount_due,
        notes=invoice.notes,
        confirmed_at=invoice.confirmed_at,
        paid_at=invoice.paid_at,
        cancelled_at=invoice.cancelled_at,
        lines=[InvoiceLineResponse.model_validate(l) for l in invoice.lines],
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )


# ---------------------------------------------------------------------------
# Tax Rules CRUD
# ---------------------------------------------------------------------------


def list_tax_rules(db: Session, is_active: Optional[bool] = None) -> List[TaxRule]:
    query = db.query(TaxRule)
    if is_active is not None:
        query = query.filter(TaxRule.is_active == is_active)
    return query.order_by(TaxRule.id.asc()).all()


def create_tax_rule(db: Session, payload: TaxRuleCreateRequest, actor: User) -> TaxRule:
    if (
        payload.effective_from
        and payload.effective_until
        and payload.effective_until < payload.effective_from
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tax rule effective_until cannot be earlier than effective_from.",
        )

    code = (payload.code or f"TAX-{secrets.token_hex(3).upper()}").strip().upper()
    existing = db.query(TaxRule).filter(TaxRule.code == code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tax rule with code '{code}' already exists.",
        )

    if payload.is_default:
        db.query(TaxRule).filter(TaxRule.is_default.is_(True)).update({"is_default": False})

    rule = TaxRule(
        name=payload.name.strip(),
        code=code,
        rate=quantize_money(payload.rate),
        region=payload.region,
        category=payload.category,
        effective_from=payload.effective_from,
        effective_until=payload.effective_until,
        is_default=payload.is_default,
        is_active=payload.is_active,
    )
    db.add(rule)
    db.flush()
    log_audit_event(
        db,
        action="tax_rule.create",
        entity_type="tax_rule",
        entity_id=rule.id,
        actor=actor,
        metadata={"code": rule.code, "rate": str(rule.rate)},
    )
    db.commit()
    db.refresh(rule)
    return rule


def update_tax_rule(
    db: Session, tax_rule_id: int, payload: TaxRuleUpdateRequest, actor: User
) -> TaxRule:
    rule = db.query(TaxRule).filter(TaxRule.id == tax_rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tax rule not found.")

    update_data = payload.model_dump(exclude_unset=True)
    if update_data.get("is_default"):
        db.query(TaxRule).filter(TaxRule.id != tax_rule_id).update({"is_default": False})

    for field, value in update_data.items():
        setattr(rule, field, value)

    log_audit_event(
        db,
        action="tax_rule.update",
        entity_type="tax_rule",
        entity_id=rule.id,
        actor=actor,
        metadata=update_data,
    )
    db.commit()
    db.refresh(rule)
    return rule


# ---------------------------------------------------------------------------
# Discounts CRUD
# ---------------------------------------------------------------------------


def list_discounts(db: Session, is_active: Optional[bool] = None) -> List[Discount]:
    query = db.query(Discount)
    if is_active is not None:
        query = query.filter(Discount.is_active == is_active)
    return query.order_by(Discount.id.desc()).all()


def create_discount(db: Session, payload: DiscountCreateRequest, actor: User) -> Discount:
    if payload.start_date and payload.end_date and payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discount end_date cannot be earlier than start_date.",
        )
    if payload.discount_type == "percentage" and payload.value > Decimal("100.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Percentage discount value cannot exceed 100%.",
        )

    code = payload.code.strip().upper()
    existing = db.query(Discount).filter(Discount.code == code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Discount with code '{code}' already exists.",
        )

    discount = Discount(
        name=payload.name.strip(),
        code=code,
        discount_type=payload.discount_type,
        value=quantize_money(payload.value),
        min_purchase_amount=quantize_money(payload.min_purchase_amount),
        min_quantity=payload.min_quantity,
        product_id=payload.product_id,
        applicable_to=payload.applicable_to,
        start_date=payload.start_date,
        end_date=payload.end_date,
        usage_limit=payload.usage_limit,
        usage_count=0,
        is_active=payload.is_active,
    )
    db.add(discount)
    db.flush()
    log_audit_event(
        db,
        action="discount.create",
        entity_type="discount",
        entity_id=discount.id,
        actor=actor,
        metadata={"code": discount.code, "type": discount.discount_type, "value": str(discount.value)},
    )
    db.commit()
    db.refresh(discount)
    return discount


def update_discount(
    db: Session, discount_id: int, payload: DiscountUpdateRequest, actor: User
) -> Discount:
    discount = db.query(Discount).filter(Discount.id == discount_id).first()
    if not discount:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(discount, field, value)

    log_audit_event(
        db,
        action="discount.update",
        entity_type="discount",
        entity_id=discount.id,
        actor=actor,
        metadata=update_data,
    )
    db.commit()
    db.refresh(discount)
    return discount


# ---------------------------------------------------------------------------
# Automated Billing & Invoice Generation (Idempotent + SKIP LOCKED Queue)
# ---------------------------------------------------------------------------


def generate_invoice_for_subscription_period(
    db: Session,
    subscription: Subscription,
    period_start: Optional[date] = None,
    auto_confirm: bool = True,
    advance_next_billing_date: bool = True,
    actor: Optional[User] = None,
    reject_if_duplicate: bool = True,
) -> Tuple[Invoice, bool]:
    """Generate an immutable invoice for a subscription's billing period.
    Enforces idempotency via both BillingJob queue and uq_invoice_subscription_billing_period.
    Returns (invoice, was_newly_created).
    """
    if subscription.state not in ("active", "confirmed", "past_due"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate billing invoice for subscription in state '{subscription.state}'.",
        )

    anchor_start = period_start or subscription.next_billing_date or subscription.start_date
    p_start, p_end, next_b_date = compute_billing_period(
        anchor_start, subscription.plan.billing_interval
    )

    # Check if an invoice already exists for (subscription_id, p_start, p_end)
    existing_invoice = (
        db.query(Invoice)
        .filter(
            Invoice.subscription_id == subscription.id,
            Invoice.billing_period_start == p_start,
            Invoice.billing_period_end == p_end,
        )
        .first()
    )
    if existing_invoice:
        if reject_if_duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Duplicate invoice prevented: Invoice '{existing_invoice.invoice_number}' "
                    f"already exists for subscription '{subscription.subscription_number}' "
                    f"and billing period {p_start} to {p_end}."
                ),
            )
        return existing_invoice, False

    # Create or claim a BillingJob using FOR UPDATE SKIP LOCKED semantics
    job = (
        db.query(BillingJob)
        .filter(
            BillingJob.subscription_id == subscription.id,
            BillingJob.billing_period_start == p_start,
            BillingJob.billing_period_end == p_end,
        )
        .with_for_update(skip_locked=True)
        .first()
    )
    now_utc = datetime.now(timezone.utc)
    if not job:
        job = BillingJob(
            subscription_id=subscription.id,
            billing_period_start=p_start,
            billing_period_end=p_end,
            scheduled_at=now_utc,
            status="processing",
            locked_at=now_utc,
            worker_id="billing-worker-1",
            attempts=1,
        )
        db.add(job)
        db.flush()
    else:
        job.status = "processing"
        job.locked_at = now_utc
        job.attempts += 1

    # Snapshot line items from subscription lines using stored unit prices and tax rates
    raw_lines = [
        {
            "product_id": l.product_id,
            "variant_id": l.variant_id,
            "tax_rule_id": l.tax_rule_id,
            "description": l.description,
            "quantity": l.quantity,
            "unit_price": l.unit_price,
            "tax_rate": l.tax_rate,
        }
        for l in subscription.lines
    ]

    # Try applying subscription's discount if still eligible; if expired/exhausted, fall back to no discount
    discount_id_to_use = subscription.discount_id
    try:
        calc = calculate_order_totals(
            db,
            raw_lines=raw_lines,
            reference_date=p_start,
            discount_id=discount_id_to_use,
            consume_discount=False,
        )
    except HTTPException:
        calc = calculate_order_totals(
            db,
            raw_lines=raw_lines,
            reference_date=p_start,
            discount_id=None,
            consume_discount=False,
        )

    issue_dt = date.today()
    due_dt = max(issue_dt, p_start) + timedelta(days=subscription.payment_term_days or 14)
    inv_state = "confirmed" if auto_confirm else "draft"
    pay_status = "overdue" if (inv_state == "confirmed" and due_dt < issue_dt) else "unpaid"

    inv_number = _next_invoice_number(db)
    invoice = Invoice(
        invoice_number=inv_number,
        subscription_id=subscription.id,
        customer_id=subscription.customer_id,
        discount_id=calc["discount"].id if calc["discount"] else None,
        billing_period_start=p_start,
        billing_period_end=p_end,
        issue_date=issue_dt,
        due_date=due_dt,
        state=inv_state,
        payment_status=pay_status,
        subtotal=calc["subtotal"],
        discount_amount=calc["discount_amount"],
        tax_amount=calc["tax_amount"],
        total=calc["total"],
        amount_paid=Decimal("0.00"),
        amount_due=calc["total"],
        notes=f"Recurring billing invoice for {subscription.subscription_number} ({p_start} to {p_end})",
        confirmed_at=now_utc if auto_confirm else None,
    )

    try:
        db.add(invoice)
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate invoice for this subscription and billing period prevented by database constraint.",
        ) from exc

    for item in calc["lines"]:
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                product_id=item["product_id"],
                variant_id=item["variant_id"],
                tax_rule_id=item["tax_rule_id"],
                description=item["description"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                tax_rate=item["tax_rate"],
                line_subtotal=item["line_subtotal"],
                line_tax=item["line_tax"],
                line_total=item["line_total"],
            )
        )

    if advance_next_billing_date:
        subscription.next_billing_date = next_b_date
        # Check auto-close if subscription reached expiry_date and plan.auto_close is True
        if (
            subscription.plan.auto_close
            and subscription.expiry_date
            and next_b_date >= subscription.expiry_date
        ):
            subscription.state = "closed"
            subscription.closed_at = now_utc
            subscription.next_billing_date = None

    job.status = "completed"
    job.invoice_id = invoice.id
    job.completed_at = now_utc

    log_audit_event(
        db,
        action="invoice.generate",
        entity_type="invoice",
        entity_id=invoice.id,
        actor=actor,
        metadata={
            "invoice_number": invoice.invoice_number,
            "subscription_id": subscription.id,
            "period_start": str(p_start),
            "period_end": str(p_end),
            "total": str(invoice.total),
        },
    )
    db.commit()
    db.refresh(invoice)
    return invoice, True


def run_automated_billing_cycle(
    db: Session,
    target_date: Optional[date] = None,
    auto_confirm: bool = True,
    actor: Optional[User] = None,
) -> BillingRunSummaryResponse:
    """Detect all active subscriptions due for billing on or before target_date,
    prevent missed billing periods, prevent duplicate invoices, and auto-close expired plans.
    """
    ref_date = target_date or date.today()
    due_subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.state == "active",
            Subscription.next_billing_date.isnot(None),
            Subscription.next_billing_date <= ref_date,
        )
        .with_for_update(skip_locked=True)
        .all()
    )

    evaluated = len(due_subscriptions)
    generated_invoices: List[InvoiceResponse] = []
    skipped = 0
    auto_closed = 0

    for sub in due_subscriptions:
        # Handle auto-close if already past expiry before billing
        if sub.plan.auto_close and sub.expiry_date and sub.next_billing_date >= sub.expiry_date:
            sub.state = "closed"
            sub.closed_at = datetime.now(timezone.utc)
            sub.next_billing_date = None
            auto_closed += 1
            db.commit()
            continue

        # Catch up any missed billing periods up to ref_date (bounded to max 12 cycles per run for safety)
        cycles = 0
        while (
            sub.state == "active"
            and sub.next_billing_date is not None
            and sub.next_billing_date <= ref_date
            and cycles < 12
        ):
            cycles += 1
            current_period_start = sub.next_billing_date
            inv, created = generate_invoice_for_subscription_period(
                db,
                subscription=sub,
                period_start=current_period_start,
                auto_confirm=auto_confirm,
                advance_next_billing_date=True,
                actor=actor,
                reject_if_duplicate=False,
            )
            if created:
                generated_invoices.append(format_invoice_response(db, inv))
            else:
                skipped += 1
                # Still advance next_billing_date if stuck on an already-billed period
                _, _, next_dt = compute_billing_period(
                    current_period_start, sub.plan.billing_interval
                )
                sub.next_billing_date = next_dt
                db.commit()

            if sub.state == "closed":
                auto_closed += 1
                break

    return BillingRunSummaryResponse(
        target_date=ref_date,
        evaluated_subscriptions=evaluated,
        generated_count=len(generated_invoices),
        skipped_duplicates=skipped,
        auto_closed_subscriptions=auto_closed,
        invoices=generated_invoices,
    )


def list_invoices(
    db: Session,
    current_user: User,
    state: Optional[str] = None,
    payment_status: Optional[str] = None,
    customer_id: Optional[int] = None,
    subscription_id: Optional[int] = None,
    overdue_only: bool = False,
) -> List[InvoiceResponse]:
    query = db.query(Invoice)
    if current_user.role == "customer":
        own_customer = get_customer_for_user(db, current_user)
        if not own_customer:
            return []
        query = query.filter(Invoice.customer_id == own_customer.id)
    elif customer_id is not None:
        query = query.filter(Invoice.customer_id == customer_id)

    if subscription_id is not None:
        query = query.filter(Invoice.subscription_id == subscription_id)
    if state:
        query = query.filter(Invoice.state == state)

    rows = query.order_by(Invoice.id.desc()).all()
    formatted = [format_invoice_response(db, inv) for inv in rows]

    if payment_status:
        formatted = [inv for inv in formatted if inv.payment_status == payment_status]
    if overdue_only:
        formatted = [inv for inv in formatted if inv.is_overdue]
    return formatted


def get_invoice_detail(
    db: Session, invoice_id: int, current_user: User
) -> InvoiceResponse:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    enforce_customer_ownership(db, current_user, invoice.customer_id)
    return format_invoice_response(db, invoice)


def confirm_invoice(
    db: Session, invoice_id: int, actor: User
) -> InvoiceResponse:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    if invoice.state != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only draft invoices can be confirmed (current state: '{invoice.state}').",
        )
    invoice.state = "confirmed"
    invoice.confirmed_at = datetime.now(timezone.utc)
    sync_invoice_overdue_state(db, invoice)
    log_audit_event(
        db,
        action="invoice.confirm",
        entity_type="invoice",
        entity_id=invoice.id,
        actor=actor,
        metadata={"invoice_number": invoice.invoice_number},
    )
    db.commit()
    db.refresh(invoice)
    return format_invoice_response(db, invoice)


def cancel_invoice(
    db: Session, invoice_id: int, actor: User
) -> InvoiceResponse:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    if invoice.state == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already cancelled.",
        )
    if invoice.state == "paid" or invoice.amount_paid > Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel an invoice that already has recorded payments.",
        )
    invoice.state = "cancelled"
    invoice.payment_status = "cancelled"
    invoice.amount_due = Decimal("0.00")
    invoice.cancelled_at = datetime.now(timezone.utc)
    log_audit_event(
        db,
        action="invoice.cancel",
        entity_type="invoice",
        entity_id=invoice.id,
        actor=actor,
        metadata={"invoice_number": invoice.invoice_number},
    )
    db.commit()
    db.refresh(invoice)
    return format_invoice_response(db, invoice)


def render_invoice_html(invoice_resp: InvoiceResponse) -> str:
    """Render a professional print-ready HTML invoice representation."""
    rows_html = "".join(
        f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #e2e8f0;">{line.description}</td>
            <td style="padding:10px;border-bottom:1px solid #e2e8f0;text-align:center;">{line.quantity}</td>
            <td style="padding:10px;border-bottom:1px solid #e2e8f0;text-align:right;">${line.unit_price:.2f}</td>
            <td style="padding:10px;border-bottom:1px solid #e2e8f0;text-align:right;">{line.tax_rate:.2f}%</td>
            <td style="padding:10px;border-bottom:1px solid #e2e8f0;text-align:right;">${line.line_tax:.2f}</td>
            <td style="padding:10px;border-bottom:1px solid #e2e8f0;text-align:right;font-weight:600;">${line.line_total:.2f}</td>
        </tr>
        """
        for line in invoice_resp.lines
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>Invoice {invoice_resp.invoice_number}</title>
    <style>
        body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; color: #0f172a; margin: 40px; }}
        .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #1e293b; padding-bottom: 20px; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 999px; background: #e0e7ff; color: #3730a3; font-weight: 600; text-transform: uppercase; font-size: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
        th {{ background: #f8fafc; padding: 12px 10px; text-align: left; font-size: 12px; text-transform: uppercase; color: #475569; border-bottom: 2px solid #cbd5e1; }}
        .totals {{ margin-top: 24px; width: 320px; margin-left: auto; }}
        .totals-row {{ display: flex; justify-content: space-between; padding: 6px 0; }}
        .totals-row.grand {{ border-top: 2px solid #0f172a; font-size: 18px; font-weight: 700; padding-top: 10px; }}
        @media print {{ .no-print {{ display: none; }} }}
    </style>
</head>
<body>
    <div class="no-print" style="margin-bottom:20px;">
        <button onclick="window.print()" style="padding:8px 16px;background:#2563eb;color:#fff;border:none;border-radius:6px;cursor:pointer;">Print / Save as PDF</button>
    </div>
    <div class="header">
        <div>
            <h1 style="margin:0;font-size:24px;">INVOICE {invoice_resp.invoice_number}</h1>
            <p style="margin:4px 0;color:#64748b;">Subscription: {invoice_resp.subscription_number or invoice_resp.subscription_id}</p>
            <p style="margin:4px 0;color:#64748b;">Billing Period: {invoice_resp.billing_period_start} to {invoice_resp.billing_period_end}</p>
        </div>
        <div style="text-align:right;">
            <span class="badge">{invoice_resp.state} / {invoice_resp.payment_status}</span>
            <p style="margin:8px 0 4px;"><strong>Issue Date:</strong> {invoice_resp.issue_date}</p>
            <p style="margin:4px 0;"><strong>Due Date:</strong> {invoice_resp.due_date}</p>
        </div>
    </div>
    <div style="margin-top:20px;">
        <h3 style="margin:0 0 6px;font-size:14px;color:#64748b;text-transform:uppercase;">Billed To</h3>
        <p style="margin:2px 0;font-weight:600;">{invoice_resp.customer_name or 'Customer'}</p>
        <p style="margin:2px 0;color:#475569;">{invoice_resp.customer_email or ''}</p>
        <p style="margin:2px 0;color:#475569;">{invoice_resp.customer_address or ''}</p>
    </div>
    <table>
        <thead>
            <tr>
                <th>Description</th>
                <th style="text-align:center;">Qty</th>
                <th style="text-align:right;">Unit Price</th>
                <th style="text-align:right;">Tax Rate</th>
                <th style="text-align:right;">Tax</th>
                <th style="text-align:right;">Line Total</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    <div class="totals">
        <div class="totals-row"><span>Subtotal:</span><span>${invoice_resp.subtotal:.2f}</span></div>
        <div class="totals-row"><span>Discount:</span><span>-${invoice_resp.discount_amount:.2f}</span></div>
        <div class="totals-row"><span>Tax:</span><span>${invoice_resp.tax_amount:.2f}</span></div>
        <div class="totals-row grand"><span>Total:</span><span>${invoice_resp.total:.2f}</span></div>
        <div class="totals-row"><span>Amount Paid:</span><span>${invoice_resp.amount_paid:.2f}</span></div>
        <div class="totals-row" style="font-weight:700;color:#dc2626;"><span>Balance Due:</span><span>${invoice_resp.amount_due:.2f}</span></div>
    </div>
</body>
</html>"""


def generate_minimal_pdf_bytes(invoice_resp: InvoiceResponse) -> bytes:
    """Generate a valid standalone PDF-1.4 document with the invoice details."""
    lines_text = [
        f"INVOICE: {invoice_resp.invoice_number}",
        f"Customer: {invoice_resp.customer_name or ''} ({invoice_resp.customer_email or ''})",
        f"Subscription: {invoice_resp.subscription_number or invoice_resp.subscription_id}",
        f"Billing Period: {invoice_resp.billing_period_start} to {invoice_resp.billing_period_end}",
        f"Issue Date: {invoice_resp.issue_date} | Due Date: {invoice_resp.due_date}",
        f"Status: {invoice_resp.state.upper()} / {invoice_resp.payment_status.upper()}",
        "------------------------------------------------------------",
    ]
    for idx, line in enumerate(invoice_resp.lines, start=1):
        lines_text.append(
            f"{idx}. {line.description} | Qty: {line.quantity} | Unit: ${line.unit_price:.2f} | Tax: ${line.line_tax:.2f} | Total: ${line.line_total:.2f}"
        )
    lines_text.extend(
        [
            "------------------------------------------------------------",
            f"Subtotal: ${invoice_resp.subtotal:.2f} | Discount: -${invoice_resp.discount_amount:.2f} | Tax: ${invoice_resp.tax_amount:.2f}",
            f"Grand Total: ${invoice_resp.total:.2f} | Paid: ${invoice_resp.amount_paid:.2f} | Balance Due: ${invoice_resp.amount_due:.2f}",
        ]
    )

    content_ops = ["BT", "/F1 11 Tf", "50 760 Td", "16 TL"]
    for text_line in lines_text:
        safe = (
            text_line.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        content_ops.append(f"({safe}) Tj T*")
    content_ops.append("ET")
    stream_bytes = "\n".join(content_ops).encode("latin-1", errors="replace")

    objs = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
        + stream_bytes
        + b"\nendstream\nendobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(pdf)

