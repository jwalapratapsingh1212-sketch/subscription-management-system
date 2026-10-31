"""HTTP endpoints for subscription plan management."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user, require_staff_or_admin
from app.models import User
from app.plans.schemas import PlanCreateRequest, PlanResponse, PlanUpdateRequest
from app.plans.service import create_plan, get_plan, list_plans, update_plan

router = APIRouter(prefix="/plans", tags=["Subscription Plans"])


@router.get("", response_model=List[PlanResponse])
def get_plans_list(
    billing_interval: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List subscription plans."""
    return list_plans(db, billing_interval=billing_interval, is_active=is_active)


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def post_plan(
    payload: PlanCreateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Create a new subscription plan (Staff or Admin)."""
    return create_plan(db, payload, staff_user)


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan_detail(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a subscription plan by ID."""
    return get_plan(db, plan_id)


@router.patch("/{plan_id}", response_model=PlanResponse)
def patch_plan(
    plan_id: int,
    payload: PlanUpdateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Update a subscription plan (Staff or Admin)."""
    return update_plan(db, plan_id, payload, staff_user)

