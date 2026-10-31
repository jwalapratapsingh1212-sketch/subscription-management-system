"""Business logic for quotations, quotation templates, and subscription lifecycle state machine."""
from datetime import date, datetime, timedelta, timezone
import json
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.core.financials import calculate_order_totals, compute_billing_period
from app.core.permissions import enforce_customer_ownership, get_customer_for_user
from app.models import (
    Customer,
    Plan,
    Quotation,
    QuotationLine,
    QuotationTemplate,
    Subscription,
    SubscriptionLine,
    User,
)
from app.plans.service import validate_plan_available_for_subscription
from app.subscriptions.schemas import (
    OrderLineResponse,
    QuotationConfirmRequest,
    QuotationCreateRequest,
    QuotationResponse,
    QuotationTemplateCreate,
    QuotationUpdateRequest,
    SubscriptionCreateRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)

# Explicit valid state transitions for the Subscription State Machine
ALLOWED_SUBSCRIPTION_TRANSITIONS = {
    "draft": {"quotation", "confirmed", "active", "closed"},
    "quotation": {"confirmed", "active", "closed"},
    "confirmed": {"active", "closed"},
    "active": {"paused", "past_due", "closed", "active"},
    "paused": {"active", "closed"},
    "past_due": {"active", "closed"},
    "closed": set(),  # Closed is terminal unless explicitly renewed if renewal_allowed
}


def _next_business_number(db: Session, model_cls, prefix: str) -> str:
    count = db.query(model_cls).count() + 1
    year = date.today().year
    candidate = f"{prefix}-{year}-{count:04d}"
    while (
        db.query(model_cls)
        .filter(getattr(model_cls, f"{model_cls.__tablename__[:-1]}_number") == candidate)
        .first()
        is not None
    ):
        count += 1
        candidate = f"{prefix}-{year}-{count:04d}"
    return candidate


def format_quotation_response(db: Session, quote: Quotation) -> QuotationResponse:
    sub = (
        db.query(Subscription)
        .filter(Subscription.quotation_id == quote.id)
        .first()
    )
    return QuotationResponse(
        id=quote.id,
        quotation_number=quote.quotation_number,
        customer_id=quote.customer_id,
        customer_name=quote.customer.name if quote.customer else None,
        plan_id=quote.plan_id,
        plan_name=quote.plan.name if quote.plan else None,
        template_id=quote.template_id,
        discount_id=quote.discount_id,
        status=quote.status,
        valid_until=quote.valid_until,
        start_date=quote.start_date,
        payment_terms=quote.payment_terms,
        notes=quote.notes,
        subtotal=quote.subtotal,
        discount_amount=quote.discount_amount,
        tax_amount=quote.tax_amount,
        total=quote.total,
        lines=[OrderLineResponse.model_validate(l) for l in quote.lines],
        subscription_id=sub.id if sub else None,
        created_at=quote.created_at,
        updated_at=quote.updated_at,
    )


def format_subscription_response(sub: Subscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=sub.id,
        subscription_number=sub.subscription_number,
        customer_id=sub.customer_id,
        customer_name=sub.customer.name if sub.customer else None,
        plan_id=sub.plan_id,
        plan_name=sub.plan.name if sub.plan else None,
        billing_interval=sub.plan.billing_interval if sub.plan else None,
        quotation_id=sub.quotation_id,
        discount_id=sub.discount_id,
        state=sub.state,
        start_date=sub.start_date,
        expiry_date=sub.expiry_date,
        next_billing_date=sub.next_billing_date,
        paused_at=sub.paused_at,
        closed_at=sub.closed_at,
        payment_terms=sub.payment_terms,
        payment_term_days=sub.payment_term_days,
        auto_renew=sub.auto_renew,
        notes=sub.notes,
        recurring_subtotal=sub.recurring_subtotal,
        recurring_discount=sub.recurring_discount,
        recurring_tax=sub.recurring_tax,
        recurring_total=sub.recurring_total,
        lines=[OrderLineResponse.model_validate(l) for l in sub.lines],
        created_at=sub.created_at,
        updated_at=sub.updated_at,
    )


# ---------------------------------------------------------------------------
# Quotation Templates
# ---------------------------------------------------------------------------


def list_quotation_templates(db: Session) -> List[QuotationTemplate]:
    return (
        db.query(QuotationTemplate)
        .filter(QuotationTemplate.is_active.is_(True))
        .order_by(QuotationTemplate.id.asc())
        .all()
    )


def create_quotation_template(
    db: Session, payload: QuotationTemplateCreate, actor: User
) -> QuotationTemplate:
    plan = db.query(Plan).filter(Plan.id == payload.plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    existing = (
        db.query(QuotationTemplate)
        .filter(QuotationTemplate.name == payload.name.strip())
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A quotation template with this name already exists.",
        )

    lines_serialized = json.dumps(
        [line.model_dump(mode="json") for line in payload.default_lines]
    )
    tpl = QuotationTemplate(
        name=payload.name.strip(),
        description=payload.description,
        plan_id=plan.id,
        validity_days=payload.validity_days,
        payment_terms=payload.payment_terms,
        notes=payload.notes,
        default_lines_json=lines_serialized,
        is_active=payload.is_active,
    )
    db.add(tpl)
    db.flush()
    log_audit_event(
        db,
        action="quotation_template.create",
        entity_type="quotation_template",
        entity_id=tpl.id,
        actor=actor,
        metadata={"name": tpl.name},
    )
    db.commit()
    db.refresh(tpl)
    return tpl


# ---------------------------------------------------------------------------
# Quotations
# ---------------------------------------------------------------------------


def list_quotations(
    db: Session,
    current_user: User,
    status_filter: Optional[str] = None,
    customer_id: Optional[int] = None,
) -> List[QuotationResponse]:
    query = db.query(Quotation)
    if current_user.role == "customer":
        own_customer = get_customer_for_user(db, current_user)
        if not own_customer:
            return []
        query = query.filter(Quotation.customer_id == own_customer.id)
    elif customer_id is not None:
        query = query.filter(Quotation.customer_id == customer_id)

    if status_filter:
        query = query.filter(Quotation.status == status_filter)

    rows = query.order_by(Quotation.id.desc()).all()
    return [format_quotation_response(db, q) for q in rows]


def create_quotation(
    db: Session, payload: QuotationCreateRequest, actor: User
) -> QuotationResponse:
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    plan = db.query(Plan).filter(Plan.id == payload.plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")

    raw_lines = [line.model_dump() for line in payload.lines]
    valid_until = payload.valid_until
    payment_terms = payload.payment_terms
    notes = payload.notes

    if payload.template_id is not None:
        tpl = (
            db.query(QuotationTemplate)
            .filter(QuotationTemplate.id == payload.template_id)
            .first()
        )
        if not tpl:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quotation template not found.",
            )
        if not raw_lines and tpl.default_lines_json:
            raw_lines = json.loads(tpl.default_lines_json)
        if not valid_until:
            valid_until = date.today() + timedelta(days=tpl.validity_days)
        if not payment_terms:
            payment_terms = tpl.payment_terms
        if not notes and tpl.notes:
            notes = tpl.notes

    if not valid_until:
        valid_until = date.today() + timedelta(days=30)

    ref_date = payload.start_date or date.today()
    total_qty = sum((int(l["quantity"]) for l in raw_lines), 0)
    validate_plan_available_for_subscription(plan, ref_date, total_qty)

    calc = calculate_order_totals(
        db,
        raw_lines=raw_lines,
        reference_date=ref_date,
        discount_id=payload.discount_id,
        discount_code=payload.discount_code,
        consume_discount=False,
    )

    quote_number = _next_business_number(db, Quotation, "QT")
    quotation = Quotation(
        quotation_number=quote_number,
        customer_id=customer.id,
        plan_id=plan.id,
        template_id=payload.template_id,
        discount_id=calc["discount"].id if calc["discount"] else None,
        status=payload.status,
        valid_until=valid_until,
        start_date=ref_date,
        payment_terms=payment_terms or "Net 14",
        notes=notes,
        subtotal=calc["subtotal"],
        discount_amount=calc["discount_amount"],
        tax_amount=calc["tax_amount"],
        total=calc["total"],
        created_by_id=actor.id,
    )
    db.add(quotation)
    db.flush()

    for item in calc["lines"]:
        q_line = QuotationLine(
            quotation_id=quotation.id,
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
        db.add(q_line)

    log_audit_event(
        db,
        action="quotation.create",
        entity_type="quotation",
        entity_id=quotation.id,
        actor=actor,
        metadata={
            "quotation_number": quotation.quotation_number,
            "customer_id": customer.id,
            "total": str(quotation.total),
        },
    )
    db.commit()
    db.refresh(quotation)
    return format_quotation_response(db, quotation)


def get_quotation_detail(
    db: Session, quotation_id: int, current_user: User
) -> QuotationResponse:
    quote = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
    enforce_customer_ownership(db, current_user, quote.customer_id)
    return format_quotation_response(db, quote)


def update_quotation(
    db: Session, quotation_id: int, payload: QuotationUpdateRequest, actor: User
) -> QuotationResponse:
    quote = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
    if quote.status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmed quotations cannot be modified.",
        )

    if payload.valid_until is not None:
        quote.valid_until = payload.valid_until
    if payload.start_date is not None:
        quote.start_date = payload.start_date
    if payload.payment_terms is not None:
        quote.payment_terms = payload.payment_terms
    if payload.notes is not None:
        quote.notes = payload.notes
    if payload.status is not None:
        quote.status = payload.status

    if payload.lines is not None or payload.discount_id is not None or payload.discount_code is not None:
        raw_lines = (
            [l.model_dump() for l in payload.lines]
            if payload.lines is not None
            else [
                {
                    "product_id": l.product_id,
                    "variant_id": l.variant_id,
                    "tax_rule_id": l.tax_rule_id,
                    "description": l.description,
                    "quantity": l.quantity,
                    "unit_price": l.unit_price,
                    "tax_rate": l.tax_rate,
                }
                for l in quote.lines
            ]
        )
        ref_date = quote.start_date or date.today()
        total_qty = sum((int(l["quantity"]) for l in raw_lines), 0)
        validate_plan_available_for_subscription(quote.plan, ref_date, total_qty)
        calc = calculate_order_totals(
            db,
            raw_lines=raw_lines,
            reference_date=ref_date,
            discount_id=payload.discount_id if payload.discount_id is not None else quote.discount_id,
            discount_code=payload.discount_code,
            consume_discount=False,
        )
        quote.discount_id = calc["discount"].id if calc["discount"] else None
        quote.subtotal = calc["subtotal"]
        quote.discount_amount = calc["discount_amount"]
        quote.tax_amount = calc["tax_amount"]
        quote.total = calc["total"]

        db.query(QuotationLine).filter(QuotationLine.quotation_id == quote.id).delete()
        for item in calc["lines"]:
            db.add(
                QuotationLine(
                    quotation_id=quote.id,
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

    log_audit_event(
        db,
        action="quotation.update",
        entity_type="quotation",
        entity_id=quote.id,
        actor=actor,
        metadata={"status": quote.status, "total": str(quote.total)},
    )
    db.commit()
    db.refresh(quote)
    return format_quotation_response(db, quote)


def confirm_quotation_to_subscription(
    db: Session,
    quotation_id: int,
    payload: QuotationConfirmRequest,
    current_user: User,
) -> SubscriptionResponse:
    """Confirm a valid quotation and atomically convert it into a Subscription."""
    quote = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")

    enforce_customer_ownership(db, current_user, quote.customer_id)

    if quote.status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quotation has already been confirmed.",
        )
    if quote.status in ("cancelled", "expired"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot confirm a quotation with status '{quote.status}'.",
        )

    today = date.today()
    if quote.valid_until < today:
        quote.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quotation expired on {quote.valid_until} and can no longer be confirmed.",
        )

    start_dt = payload.start_date or quote.start_date or today
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
        for l in quote.lines
    ]
    total_qty = sum((int(l["quantity"]) for l in raw_lines), 0)
    validate_plan_available_for_subscription(quote.plan, start_dt, total_qty)

    # Re-validate discount and consume usage count atomically on confirmation
    calc = calculate_order_totals(
        db,
        raw_lines=raw_lines,
        reference_date=start_dt,
        discount_id=quote.discount_id,
        consume_discount=True,
    )

    _, period_end, next_date = compute_billing_period(start_dt, quote.plan.billing_interval)
    target_state = "active" if payload.activate_immediately else "confirmed"

    sub_number = _next_business_number(db, Subscription, "SUB")
    subscription = Subscription(
        subscription_number=sub_number,
        customer_id=quote.customer_id,
        plan_id=quote.plan_id,
        quotation_id=quote.id,
        discount_id=quote.discount_id,
        state=target_state,
        start_date=start_dt,
        expiry_date=next_date,
        next_billing_date=start_dt if target_state == "active" else None,
        payment_terms=quote.payment_terms,
        payment_term_days=quote.plan.default_payment_term_days,
        auto_renew=quote.plan.renewal_allowed,
        notes=quote.notes,
        recurring_subtotal=calc["subtotal"],
        recurring_discount=calc["discount_amount"],
        recurring_tax=calc["tax_amount"],
        recurring_total=calc["total"],
    )
    db.add(subscription)
    db.flush()

    for item in calc["lines"]:
        db.add(
            SubscriptionLine(
                subscription_id=subscription.id,
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

    quote.status = "confirmed"
    log_audit_event(
        db,
        action="quotation.confirm",
        entity_type="subscription",
        entity_id=subscription.id,
        actor=current_user,
        metadata={
            "quotation_id": quote.id,
            "quotation_number": quote.quotation_number,
            "subscription_number": subscription.subscription_number,
            "state": subscription.state,
        },
    )
    db.commit()
    db.refresh(subscription)
    return format_subscription_response(subscription)


# ---------------------------------------------------------------------------
# Subscriptions & Lifecycle Transitions
# ---------------------------------------------------------------------------


def list_subscriptions(
    db: Session,
    current_user: User,
    state: Optional[str] = None,
    customer_id: Optional[int] = None,
) -> List[SubscriptionResponse]:
    query = db.query(Subscription)
    if current_user.role == "customer":
        own_customer = get_customer_for_user(db, current_user)
        if not own_customer:
            return []
        query = query.filter(Subscription.customer_id == own_customer.id)
    elif customer_id is not None:
        query = query.filter(Subscription.customer_id == customer_id)

    if state:
        query = query.filter(Subscription.state == state)

    rows = query.order_by(Subscription.id.desc()).all()
    return [format_subscription_response(s) for s in rows]


def create_subscription(
    db: Session, payload: SubscriptionCreateRequest, actor: User
) -> SubscriptionResponse:
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    plan = db.query(Plan).filter(Plan.id == payload.plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")

    start_dt = payload.start_date or date.today()
    raw_lines = [l.model_dump() for l in payload.lines]
    total_qty = sum((int(l["quantity"]) for l in raw_lines), 0)
    validate_plan_available_for_subscription(plan, start_dt, total_qty)

    consume_disc = payload.initial_state in ("confirmed", "active")
    calc = calculate_order_totals(
        db,
        raw_lines=raw_lines,
        reference_date=start_dt,
        discount_id=payload.discount_id,
        discount_code=payload.discount_code,
        consume_discount=consume_disc,
    )

    _, _, next_cycle_date = compute_billing_period(start_dt, plan.billing_interval)
    expiry_dt = payload.expiry_date or next_cycle_date

    sub_number = _next_business_number(db, Subscription, "SUB")
    subscription = Subscription(
        subscription_number=sub_number,
        customer_id=customer.id,
        plan_id=plan.id,
        discount_id=calc["discount"].id if calc["discount"] else None,
        state=payload.initial_state,
        start_date=start_dt,
        expiry_date=expiry_dt,
        next_billing_date=start_dt if payload.initial_state == "active" else None,
        payment_terms=payload.payment_terms,
        payment_term_days=payload.payment_term_days or plan.default_payment_term_days,
        auto_renew=payload.auto_renew,
        notes=payload.notes,
        recurring_subtotal=calc["subtotal"],
        recurring_discount=calc["discount_amount"],
        recurring_tax=calc["tax_amount"],
        recurring_total=calc["total"],
    )
    db.add(subscription)
    db.flush()

    for item in calc["lines"]:
        db.add(
            SubscriptionLine(
                subscription_id=subscription.id,
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

    log_audit_event(
        db,
        action="subscription.create",
        entity_type="subscription",
        entity_id=subscription.id,
        actor=actor,
        metadata={
            "subscription_number": subscription.subscription_number,
            "state": subscription.state,
            "recurring_total": str(subscription.recurring_total),
        },
    )
    db.commit()
    db.refresh(subscription)
    return format_subscription_response(subscription)


def get_subscription_detail(
    db: Session, subscription_id: int, current_user: User
) -> SubscriptionResponse:
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found."
        )
    enforce_customer_ownership(db, current_user, sub.customer_id)
    return format_subscription_response(sub)


def update_subscription(
    db: Session, subscription_id: int, payload: SubscriptionUpdateRequest, actor: User
) -> SubscriptionResponse:
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found."
        )
    if sub.state == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Closed subscriptions cannot be modified.",
        )

    if payload.expiry_date is not None:
        sub.expiry_date = payload.expiry_date
    if payload.payment_terms is not None:
        sub.payment_terms = payload.payment_terms
    if payload.payment_term_days is not None:
        sub.payment_term_days = payload.payment_term_days
    if payload.auto_renew is not None:
        sub.auto_renew = payload.auto_renew
    if payload.notes is not None:
        sub.notes = payload.notes

    if payload.lines is not None:
        raw_lines = [l.model_dump() for l in payload.lines]
        total_qty = sum((int(l["quantity"]) for l in raw_lines), 0)
        validate_plan_available_for_subscription(sub.plan, sub.start_date, total_qty)
        calc = calculate_order_totals(
            db,
            raw_lines=raw_lines,
            reference_date=sub.start_date,
            discount_id=payload.discount_id if payload.discount_id is not None else sub.discount_id,
            consume_discount=False,
        )
        sub.discount_id = calc["discount"].id if calc["discount"] else None
        sub.recurring_subtotal = calc["subtotal"]
        sub.recurring_discount = calc["discount_amount"]
        sub.recurring_tax = calc["tax_amount"]
        sub.recurring_total = calc["total"]

        db.query(SubscriptionLine).filter(
            SubscriptionLine.subscription_id == sub.id
        ).delete()
        for item in calc["lines"]:
            db.add(
                SubscriptionLine(
                    subscription_id=sub.id,
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

    log_audit_event(
        db,
        action="subscription.update",
        entity_type="subscription",
        entity_id=sub.id,
        actor=actor,
    )
    db.commit()
    db.refresh(sub)
    return format_subscription_response(sub)


def transition_subscription_state(
    db: Session,
    subscription_id: int,
    action: str,
    current_user: User,
) -> SubscriptionResponse:
    """Enforce strict subscription lifecycle transitions and plan rules:
    Draft -> Quotation -> Confirmed -> Active <-> Paused / Past Due -> Closed (+ Renew).
    """
    sub = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found."
        )
    enforce_customer_ownership(db, current_user, sub.customer_id)

    plan = sub.plan
    old_state = sub.state
    now_utc = datetime.now(timezone.utc)

    if action == "send_quote":
        target_state = "quotation"
        if target_state not in ALLOWED_SUBSCRIPTION_TRANSITIONS.get(old_state, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state transition from '{old_state}' to '{target_state}'.",
            )
        sub.state = target_state

    elif action == "confirm":
        target_state = "confirmed"
        if target_state not in ALLOWED_SUBSCRIPTION_TRANSITIONS.get(old_state, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid state transition from '{old_state}' to '{target_state}'.",
            )
        sub.state = target_state

    elif action == "activate":
        target_state = "active"
        if old_state not in ("draft", "quotation", "confirmed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot activate subscription from state '{old_state}'. Use resume for paused subscriptions.",
            )
        sub.state = "active"
        if not sub.next_billing_date:
            sub.next_billing_date = sub.start_date

    elif action == "pause":
        if old_state != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only 'active' subscriptions can be paused (current state: '{old_state}').",
            )
        if not plan.pause_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plan '{plan.name}' does not allow pausing subscriptions.",
            )
        sub.state = "paused"
        sub.paused_at = now_utc

    elif action == "resume":
        if old_state != "paused":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only 'paused' subscriptions can be resumed (current state: '{old_state}').",
            )
        if not plan.resume_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plan '{plan.name}' does not allow resuming paused subscriptions.",
            )
        sub.state = "active"
        sub.paused_at = None
        if not sub.next_billing_date or sub.next_billing_date < date.today():
            sub.next_billing_date = date.today()

    elif action == "renew":
        if old_state not in ("active", "past_due", "closed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot renew subscription in state '{old_state}'.",
            )
        if not plan.renewal_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plan '{plan.name}' does not allow subscription renewal.",
            )
        anchor = sub.expiry_date or sub.next_billing_date or date.today()
        _, _, new_expiry = compute_billing_period(anchor, plan.billing_interval)
        sub.expiry_date = new_expiry
        sub.state = "active"
        sub.closed_at = None
        if not sub.next_billing_date:
            sub.next_billing_date = anchor

    elif action == "close":
        if old_state == "closed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription is already closed.",
            )
        if (
            old_state in ("active", "paused")
            and sub.expiry_date
            and date.today() < sub.expiry_date
            and not plan.early_close_allowed
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Plan '{plan.name}' does not permit early closure before expiry date "
                    f"({sub.expiry_date})."
                ),
            )
        sub.state = "closed"
        sub.closed_at = now_utc
        sub.next_billing_date = None

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported subscription lifecycle action: {action}",
        )

    log_audit_event(
        db,
        action=f"subscription.{action}",
        entity_type="subscription",
        entity_id=sub.id,
        actor=current_user,
        metadata={"from_state": old_state, "to_state": sub.state},
    )
    db.commit()
    db.refresh(sub)
    return format_subscription_response(sub)

