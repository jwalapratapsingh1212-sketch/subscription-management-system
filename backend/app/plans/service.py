"""Business logic for subscription plans, availability validation, and lifecycle flags."""
from datetime import date
import secrets
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.models import Plan, User
from app.plans.schemas import PlanCreateRequest, PlanUpdateRequest


def validate_plan_dates(available_from: Optional[date], available_until: Optional[date]) -> None:
    if available_from and available_until and available_until < available_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan available_until date cannot be earlier than available_from date.",
        )


def validate_plan_available_for_subscription(
    plan: Plan, target_date: date, total_quantity: int
) -> None:
    """Verify plan active status, availability window, and minimum quantity."""
    if not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan '{plan.name}' is currently inactive.",
        )
    if plan.available_from and target_date < plan.available_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan '{plan.name}' is not available before {plan.available_from}.",
        )
    if plan.available_until and target_date > plan.available_until:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan '{plan.name}' availability expired on {plan.available_until}.",
        )
    if total_quantity < plan.minimum_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Plan '{plan.name}' requires a minimum total quantity of "
                f"{plan.minimum_quantity} (received {total_quantity})."
            ),
        )


def list_plans(
    db: Session,
    billing_interval: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[Plan]:
    query = db.query(Plan)
    if billing_interval:
        query = query.filter(Plan.billing_interval == billing_interval)
    if is_active is not None:
        query = query.filter(Plan.is_active == is_active)
    return query.order_by(Plan.id.asc()).all()


def create_plan(db: Session, payload: PlanCreateRequest, actor: User) -> Plan:
    validate_plan_dates(payload.available_from, payload.available_until)
    code = (payload.code or f"PLN-{secrets.token_hex(3).upper()}").strip().upper()
    existing = db.query(Plan).filter(Plan.code == code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan with code '{code}' already exists.",
        )

    plan = Plan(
        code=code,
        name=payload.name.strip(),
        description=payload.description,
        billing_interval=payload.billing_interval,
        minimum_quantity=payload.minimum_quantity,
        available_from=payload.available_from,
        available_until=payload.available_until,
        trial_period_days=payload.trial_period_days,
        default_payment_term_days=payload.default_payment_term_days,
        auto_close=payload.auto_close,
        early_close_allowed=payload.early_close_allowed,
        pause_allowed=payload.pause_allowed,
        resume_allowed=payload.resume_allowed,
        renewal_allowed=payload.renewal_allowed,
        is_active=payload.is_active,
    )
    db.add(plan)
    db.flush()
    log_audit_event(
        db,
        action="plan.create",
        entity_type="plan",
        entity_id=plan.id,
        actor=actor,
        metadata={"code": plan.code, "name": plan.name, "interval": plan.billing_interval},
    )
    db.commit()
    db.refresh(plan)
    return plan


def get_plan(db: Session, plan_id: int) -> Plan:
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    return plan


def update_plan(db: Session, plan_id: int, payload: PlanUpdateRequest, actor: User) -> Plan:
    plan = get_plan(db, plan_id)
    update_data = payload.model_dump(exclude_unset=True)
    avail_from = update_data.get("available_from", plan.available_from)
    avail_until = update_data.get("available_until", plan.available_until)
    validate_plan_dates(avail_from, avail_until)

    for field, value in update_data.items():
        setattr(plan, field, value)

    log_audit_event(
        db,
        action="plan.update",
        entity_type="plan",
        entity_id=plan.id,
        actor=actor,
        metadata=update_data,
    )
    db.commit()
    db.refresh(plan)
    return plan

