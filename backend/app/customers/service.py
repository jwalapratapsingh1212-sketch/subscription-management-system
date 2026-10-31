"""Business logic for customer CRUD, ownership enforcement, and portal aggregation."""
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.core.permissions import enforce_customer_ownership, get_customer_for_user
from app.core.security import hash_password, validate_password_strength
from app.customers.schemas import (
    CustomerCreateRequest,
    CustomerResponse,
    CustomerUpdateRequest,
    PaginatedCustomerResponse,
)
from app.models import Customer, Invoice, Subscription, User


def enrich_customer(db: Session, customer: Customer) -> CustomerResponse:
    active_subs = (
        db.query(Subscription)
        .filter(
            Subscription.customer_id == customer.id,
            Subscription.state.in_(["active", "confirmed", "past_due"]),
        )
        .count()
    )
    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.customer_id == customer.id,
            Invoice.state.in_(["confirmed", "paid"]),
        )
        .all()
    )
    total_billed = sum((inv.total for inv in invoices), Decimal("0.00"))
    outstanding = sum((inv.amount_due for inv in invoices), Decimal("0.00"))

    return CustomerResponse(
        id=customer.id,
        user_id=customer.user_id,
        name=customer.name,
        company_name=customer.company_name,
        email=customer.email,
        phone=customer.phone,
        tax_id=customer.tax_id,
        billing_address=customer.billing_address,
        city=customer.city,
        state=customer.state,
        country=customer.country,
        postal_code=customer.postal_code,
        notes=customer.notes,
        is_active=customer.is_active,
        active_subscriptions_count=active_subs,
        total_billed=total_billed,
        outstanding_balance=outstanding,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )


def list_customers(
    db: Session,
    current_user: User,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedCustomerResponse:
    query = db.query(Customer)

    # Strict customer isolation if caller is a customer
    if current_user.role == "customer":
        own_customer = get_customer_for_user(db, current_user)
        if not own_customer:
            return PaginatedCustomerResponse(items=[], total=0, page=page, page_size=page_size)
        query = query.filter(Customer.id == own_customer.id)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Customer.name.ilike(term),
                Customer.email.ilike(term),
                Customer.company_name.ilike(term),
            )
        )
    if is_active is not None:
        query = query.filter(Customer.is_active == is_active)

    total = query.count()
    rows = (
        query.order_by(Customer.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedCustomerResponse(
        items=[enrich_customer(db, c) for c in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def create_customer(
    db: Session, payload: CustomerCreateRequest, actor: User
) -> CustomerResponse:
    normalized_email = payload.email.strip().lower()
    user_id = None

    if payload.password:
        validate_password_strength(payload.password)
        existing_user = db.query(User).filter(User.email == normalized_email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user account with this email already exists.",
            )
        new_user = User(
            email=normalized_email,
            full_name=payload.name.strip(),
            password_hash=hash_password(payload.password),
            role="customer",
            is_active=True,
        )
        db.add(new_user)
        db.flush()
        user_id = new_user.id

    customer = Customer(
        user_id=user_id,
        name=payload.name.strip(),
        company_name=payload.company_name,
        email=normalized_email,
        phone=payload.phone,
        tax_id=payload.tax_id,
        billing_address=payload.billing_address or "",
        city=payload.city,
        state=payload.state,
        country=payload.country or "US",
        postal_code=payload.postal_code,
        notes=payload.notes,
        is_active=True,
    )
    db.add(customer)
    db.flush()
    log_audit_event(
        db,
        action="customer.create",
        entity_type="customer",
        entity_id=customer.id,
        actor=actor,
        metadata={"name": customer.name, "email": customer.email},
    )
    db.commit()
    db.refresh(customer)
    return enrich_customer(db, customer)


def get_customer_detail(db: Session, customer_id: int, current_user: User) -> CustomerResponse:
    enforce_customer_ownership(db, current_user, customer_id)
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    return enrich_customer(db, customer)


def update_customer(
    db: Session, customer_id: int, payload: CustomerUpdateRequest, current_user: User
) -> CustomerResponse:
    enforce_customer_ownership(db, current_user, customer_id)
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")

    update_data = payload.model_dump(exclude_unset=True)
    # Customers cannot change their own active status
    if current_user.role == "customer":
        update_data.pop("is_active", None)

    for field, value in update_data.items():
        if field == "email" and value:
            value = value.strip().lower()
        setattr(customer, field, value)

    log_audit_event(
        db,
        action="customer.update",
        entity_type="customer",
        entity_id=customer.id,
        actor=current_user,
        metadata=update_data,
    )
    db.commit()
    db.refresh(customer)
    return enrich_customer(db, customer)

