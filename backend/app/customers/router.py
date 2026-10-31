"""HTTP endpoints for customer profiles and customer portal summary."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import (
    get_current_user,
    get_customer_for_user,
    require_staff_or_admin,
)
from app.customers.schemas import (
    CustomerCreateRequest,
    CustomerResponse,
    CustomerUpdateRequest,
    PaginatedCustomerResponse,
)
from app.customers.service import (
    create_customer,
    enrich_customer,
    get_customer_detail,
    list_customers,
    update_customer,
)
from app.models import User

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=PaginatedCustomerResponse)
def get_customers(
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List customers with search and pagination (scoped to own profile for Customer role)."""
    return list_customers(db, current_user, search=search, is_active=is_active, page=page, page_size=page_size)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def post_customer(
    payload: CustomerCreateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Create a new customer profile (Staff or Admin)."""
    return create_customer(db, payload, staff_user)


@router.get("/me/profile", response_model=CustomerResponse)
def get_my_customer_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the authenticated customer's own customer profile."""
    customer = get_customer_for_user(db, current_user)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No customer profile is linked to this user account.",
        )
    return enrich_customer(db, customer)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a single customer profile (enforces customer isolation)."""
    return get_customer_detail(db, customer_id, current_user)


@router.patch("/{customer_id}", response_model=CustomerResponse)
def patch_customer(
    customer_id: int,
    payload: CustomerUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a customer profile (enforces customer isolation)."""
    return update_customer(db, customer_id, payload, current_user)

