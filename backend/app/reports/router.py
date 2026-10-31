"""HTTP endpoints for Finance Dashboard, Overdue Aging, Revenue Analytics, and Audit Logs."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import (
    get_current_user,
    get_customer_for_user,
    require_staff_or_admin,
)
from app.customers.service import enrich_customer
from app.invoices.service import list_invoices
from app.models import User
from app.payments.service import list_payments
from app.reports.schemas import (
    AuditLogResponse,
    DashboardSummaryResponse,
    OverdueInvoiceItem,
    RevenueTrendItem,
)
from app.reports.service import (
    get_dashboard_summary,
    get_overdue_report,
    list_recent_audit_logs,
)
from app.subscriptions.service import list_quotations, list_subscriptions

router = APIRouter(prefix="/reports", tags=["Finance Dashboard & Reports"])


@router.get("/dashboard", response_model=DashboardSummaryResponse)
def get_dashboard(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    customer_id: Optional[int] = Query(default=None),
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Return Finance Dashboard summary distinguishing Billed Revenue, Cash Collected, and Pro-Rata Recognized Revenue."""
    return get_dashboard_summary(
        db, date_from=date_from, date_to=date_to, customer_id=customer_id
    )


@router.get("/overdue", response_model=List[OverdueInvoiceItem])
def get_overdue_invoices(
    customer_id: Optional[int] = Query(default=None),
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Return overdue invoices with aging (days_overdue) and outstanding balances."""
    return get_overdue_report(db, customer_id=customer_id)


@router.get("/revenue", response_model=List[RevenueTrendItem])
def get_revenue_trends(
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    customer_id: Optional[int] = Query(default=None),
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Return monthly revenue trend series comparing Billed Revenue, Cash Collected, and Recognized Revenue."""
    summary = get_dashboard_summary(
        db, date_from=date_from, date_to=date_to, customer_id=customer_id
    )
    return summary.revenue_trends


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Return immutable administrative and financial audit log trail."""
    return list_recent_audit_logs(db, limit=limit)


@router.get("/portal")
def get_customer_portal_bundle(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a customer-scoped summary bundle for the Customer Self-Service Portal."""
    customer = get_customer_for_user(db, current_user)
    if not customer:
        return {
            "customer": None,
            "quotations": [],
            "subscriptions": [],
            "invoices": [],
            "payments": [],
        }
    return {
        "customer": enrich_customer(db, customer),
        "quotations": list_quotations(db, current_user),
        "subscriptions": list_subscriptions(db, current_user),
        "invoices": list_invoices(db, current_user),
        "payments": list_payments(db, current_user),
    }

