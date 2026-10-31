"""HTTP endpoints for invoices, automated billing runs, tax rules, and discounts."""
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user, require_staff_or_admin
from app.invoices.schemas import (
    BillingRunSummaryResponse,
    DiscountCreateRequest,
    DiscountResponse,
    DiscountUpdateRequest,
    InvoiceGenerateRequest,
    InvoiceResponse,
    TaxRuleCreateRequest,
    TaxRuleResponse,
    TaxRuleUpdateRequest,
)
from app.invoices.service import (
    cancel_invoice,
    confirm_invoice,
    create_discount,
    create_tax_rule,
    format_invoice_response,
    generate_invoice_for_subscription_period,
    generate_minimal_pdf_bytes,
    get_invoice_detail,
    list_discounts,
    list_invoices,
    list_tax_rules,
    render_invoice_html,
    run_automated_billing_cycle,
    update_discount,
    update_tax_rule,
)
from app.models import Subscription, User

invoices_router = APIRouter(prefix="/invoices", tags=["Invoices & Automated Billing"])
discounts_router = APIRouter(prefix="/discounts", tags=["Discounts"])
tax_rules_router = APIRouter(prefix="/tax-rules", tags=["Tax Rules"])


# ---------------------------------------------------------------------------
# Invoices & Billing Endpoints
# ---------------------------------------------------------------------------


@invoices_router.get("", response_model=List[InvoiceResponse])
def get_invoices_list(
    state: Optional[str] = Query(default=None),
    payment_status: Optional[str] = Query(default=None),
    customer_id: Optional[int] = Query(default=None),
    subscription_id: Optional[int] = Query(default=None),
    overdue_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List invoices with filters (scoped to own records for Customer role)."""
    return list_invoices(
        db,
        current_user=current_user,
        state=state,
        payment_status=payment_status,
        customer_id=customer_id,
        subscription_id=subscription_id,
        overdue_only=overdue_only,
    )


@invoices_router.post(
    "/generate",
    response_model=Union[InvoiceResponse, BillingRunSummaryResponse],
    status_code=status.HTTP_201_CREATED,
)
def post_generate_invoices(
    payload: Optional[InvoiceGenerateRequest] = None,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Generate an invoice for a specific subscription or run the automated billing-day engine."""
    req = payload or InvoiceGenerateRequest()
    if req.subscription_id is not None:
        sub = (
            db.query(Subscription)
            .filter(Subscription.id == req.subscription_id)
            .first()
        )
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found."
            )
        invoice, _ = generate_invoice_for_subscription_period(
            db,
            subscription=sub,
            period_start=req.billing_period_start,
            auto_confirm=req.auto_confirm,
            advance_next_billing_date=req.advance_next_billing_date,
            actor=staff_user,
            reject_if_duplicate=True,
        )
        return format_invoice_response(db, invoice)

    return run_automated_billing_cycle(
        db,
        target_date=req.target_date,
        auto_confirm=req.auto_confirm,
        actor=staff_user,
    )


@invoices_router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve invoice details and immutable line snapshots (enforces customer isolation)."""
    return get_invoice_detail(db, invoice_id, current_user)


@invoices_router.post("/{invoice_id}/confirm", response_model=InvoiceResponse)
def post_confirm_invoice(
    invoice_id: int,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Confirm a draft invoice (Staff or Admin)."""
    return confirm_invoice(db, invoice_id, staff_user)


@invoices_router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
def post_cancel_invoice(
    invoice_id: int,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Cancel an unpaid invoice (Staff or Admin)."""
    return cancel_invoice(db, invoice_id, staff_user)


@invoices_router.get("/{invoice_id}/print", response_class=HTMLResponse)
def get_invoice_print_html(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Render a print-ready HTML representation of an invoice."""
    inv_resp = get_invoice_detail(db, invoice_id, current_user)
    return HTMLResponse(content=render_invoice_html(inv_resp))


@invoices_router.get("/{invoice_id}/pdf")
def get_invoice_pdf_download(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a PDF file for an invoice."""
    inv_resp = get_invoice_detail(db, invoice_id, current_user)
    pdf_bytes = generate_minimal_pdf_bytes(inv_resp)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{inv_resp.invoice_number}.pdf"'
        },
    )


# ---------------------------------------------------------------------------
# Discounts Endpoints
# ---------------------------------------------------------------------------


@discounts_router.get("", response_model=List[DiscountResponse])
def get_discounts_list(
    is_active: Optional[bool] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List discount rules."""
    return list_discounts(db, is_active=is_active)


@discounts_router.post(
    "", response_model=DiscountResponse, status_code=status.HTTP_201_CREATED
)
def post_discount(
    payload: DiscountCreateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Create a fixed or percentage discount rule (Staff or Admin)."""
    return create_discount(db, payload, staff_user)


@discounts_router.patch("/{discount_id}", response_model=DiscountResponse)
def patch_discount(
    discount_id: int,
    payload: DiscountUpdateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Update a discount rule (Staff or Admin)."""
    return update_discount(db, discount_id, payload, staff_user)


# ---------------------------------------------------------------------------
# Tax Rules Endpoints
# ---------------------------------------------------------------------------


@tax_rules_router.get("", response_model=List[TaxRuleResponse])
def get_tax_rules_list(
    is_active: Optional[bool] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List configurable tax rules."""
    return list_tax_rules(db, is_active=is_active)


@tax_rules_router.post(
    "", response_model=TaxRuleResponse, status_code=status.HTTP_201_CREATED
)
def post_tax_rule(
    payload: TaxRuleCreateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Create a configurable tax rule (Staff or Admin)."""
    return create_tax_rule(db, payload, staff_user)


@tax_rules_router.patch("/{tax_rule_id}", response_model=TaxRuleResponse)
def patch_tax_rule(
    tax_rule_id: int,
    payload: TaxRuleUpdateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Update a tax rule (Staff or Admin)."""
    return update_tax_rule(db, tax_rule_id, payload, staff_user)

