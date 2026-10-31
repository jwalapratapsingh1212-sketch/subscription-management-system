"""HTTP endpoints for quotation templates, quotations, and subscriptions."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user, require_staff_or_admin
from app.models import User
from app.subscriptions.schemas import (
    QuotationConfirmRequest,
    QuotationCreateRequest,
    QuotationResponse,
    QuotationTemplateCreate,
    QuotationTemplateResponse,
    QuotationUpdateRequest,
    SubscriptionCreateRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)
from app.subscriptions.service import (
    confirm_quotation_to_subscription,
    create_quotation,
    create_quotation_template,
    create_subscription,
    get_quotation_detail,
    get_subscription_detail,
    list_quotation_templates,
    list_quotations,
    list_subscriptions,
    transition_subscription_state,
    update_quotation,
    update_subscription,
)

quotations_router = APIRouter(prefix="/quotations", tags=["Quotations"])
subscriptions_router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# ---------------------------------------------------------------------------
# Quotations & Templates Endpoints
# ---------------------------------------------------------------------------


@quotations_router.get("/templates", response_model=List[QuotationTemplateResponse])
def get_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List active quotation templates."""
    return list_quotation_templates(db)


@quotations_router.post(
    "/templates",
    response_model=QuotationTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_template(
    payload: QuotationTemplateCreate,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Create a reusable quotation template (Staff or Admin)."""
    return create_quotation_template(db, payload, staff_user)


@quotations_router.get("", response_model=List[QuotationResponse])
def get_quotations_list(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    customer_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List quotations (scoped to own records for Customer role)."""
    return list_quotations(db, current_user, status_filter=status_filter, customer_id=customer_id)


@quotations_router.post("", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
def post_quotation(
    payload: QuotationCreateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Create a customer quotation (Staff or Admin)."""
    return create_quotation(db, payload, staff_user)


@quotations_router.get("/{quotation_id}", response_model=QuotationResponse)
def get_quotation(
    quotation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a single quotation (enforces customer isolation)."""
    return get_quotation_detail(db, quotation_id, current_user)


@quotations_router.patch("/{quotation_id}", response_model=QuotationResponse)
def patch_quotation(
    quotation_id: int,
    payload: QuotationUpdateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Update a draft/sent quotation (Staff or Admin)."""
    return update_quotation(db, quotation_id, payload, staff_user)


@quotations_router.post(
    "/{quotation_id}/confirm",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_confirm_quotation(
    quotation_id: int,
    payload: Optional[QuotationConfirmRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm a valid quotation and convert it into a Subscription."""
    req = payload or QuotationConfirmRequest()
    return confirm_quotation_to_subscription(db, quotation_id, req, current_user)


# ---------------------------------------------------------------------------
# Subscriptions & Lifecycle Endpoints
# ---------------------------------------------------------------------------


@subscriptions_router.get("", response_model=List[SubscriptionResponse])
def get_subscriptions_list(
    state: Optional[str] = Query(default=None),
    customer_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List subscriptions (scoped to own records for Customer role)."""
    return list_subscriptions(db, current_user, state=state, customer_id=customer_id)


@subscriptions_router.post(
    "", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED
)
def post_subscription(
    payload: SubscriptionCreateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Create a subscription directly (Staff or Admin)."""
    return create_subscription(db, payload, staff_user)


@subscriptions_router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve subscription details and line items (enforces customer isolation)."""
    return get_subscription_detail(db, subscription_id, current_user)


@subscriptions_router.patch("/{subscription_id}", response_model=SubscriptionResponse)
def patch_subscription(
    subscription_id: int,
    payload: SubscriptionUpdateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Update subscription terms or lines (Staff or Admin)."""
    return update_subscription(db, subscription_id, payload, staff_user)


@subscriptions_router.post(
    "/{subscription_id}/send-quote", response_model=SubscriptionResponse
)
def post_subscription_send_quote(
    subscription_id: int,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Transition subscription from Draft -> Quotation."""
    return transition_subscription_state(db, subscription_id, "send_quote", staff_user)


@subscriptions_router.post(
    "/{subscription_id}/confirm", response_model=SubscriptionResponse
)
def post_subscription_confirm(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Transition subscription from Draft/Quotation -> Confirmed."""
    return transition_subscription_state(db, subscription_id, "confirm", current_user)


@subscriptions_router.post(
    "/{subscription_id}/activate", response_model=SubscriptionResponse
)
def post_subscription_activate(
    subscription_id: int,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Transition subscription to Active state and initialize next_billing_date."""
    return transition_subscription_state(db, subscription_id, "activate", staff_user)


@subscriptions_router.post(
    "/{subscription_id}/pause", response_model=SubscriptionResponse
)
def post_subscription_pause(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Pause an active subscription (if plan.pause_allowed is True)."""
    return transition_subscription_state(db, subscription_id, "pause", current_user)


@subscriptions_router.post(
    "/{subscription_id}/resume", response_model=SubscriptionResponse
)
def post_subscription_resume(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resume a paused subscription (if plan.resume_allowed is True)."""
    return transition_subscription_state(db, subscription_id, "resume", current_user)


@subscriptions_router.post(
    "/{subscription_id}/renew", response_model=SubscriptionResponse
)
def post_subscription_renew(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Renew a subscription term (if plan.renewal_allowed is True)."""
    return transition_subscription_state(db, subscription_id, "renew", current_user)


@subscriptions_router.post(
    "/{subscription_id}/close", response_model=SubscriptionResponse
)
def post_subscription_close(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Close a subscription (enforces plan.early_close_allowed if before expiry_date)."""
    return transition_subscription_state(db, subscription_id, "close", current_user)

