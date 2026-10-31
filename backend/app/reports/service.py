"""High-performance reporting service for Finance Dashboard, Overdue Aging, and Revenue Analytics."""
from collections import defaultdict
from datetime import date
from decimal import Decimal
import time
from typing import Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from app.core.financials import quantize_money
from app.models import AuditLog, Customer, Invoice, Payment, Subscription
from app.reports.schemas import (
    DashboardSummaryResponse,
    OverdueInvoiceItem,
    PlanDistributionItem,
    RevenueTrendItem,
    StateDistributionItem,
)


def _normalize_to_mrr(recurring_amount: Decimal, interval: str) -> Decimal:
    if interval == "daily":
        return quantize_money(recurring_amount * Decimal("30.00"))
    if interval == "weekly":
        return quantize_money((recurring_amount * Decimal("52.00")) / Decimal("12.00"))
    if interval == "monthly":
        return quantize_money(recurring_amount)
    if interval == "yearly":
        return quantize_money(recurring_amount / Decimal("12.00"))
    return Decimal("0.00")


def _compute_pro_rata_recognition(
    net_amount: Decimal,
    period_start: date,
    period_end: date,
    as_of_date: date,
) -> tuple[Decimal, Decimal]:
    """Calculate pro-rata earned vs. deferred (unearned) revenue over [period_start, period_end]."""
    if as_of_date < period_start:
        return Decimal("0.00"), quantize_money(net_amount)
    if as_of_date >= period_end or period_end <= period_start:
        return quantize_money(net_amount), Decimal("0.00")

    total_days = max(1, (period_end - period_start).days + 1)
    elapsed_days = max(0, min(total_days, (as_of_date - period_start).days + 1))
    recognized = quantize_money(
        (net_amount * Decimal(elapsed_days)) / Decimal(total_days)
    )
    deferred = quantize_money(max(Decimal("0.00"), net_amount - recognized))
    return recognized, deferred


def get_dashboard_summary(
    db: Session,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    customer_id: Optional[int] = None,
) -> DashboardSummaryResponse:
    t0 = time.perf_counter()
    today = date_to or date.today()

    cust_query = db.query(Customer)
    if customer_id is not None:
        cust_query = cust_query.filter(Customer.id == customer_id)
    total_customers = cust_query.count()
    active_customers = cust_query.filter(Customer.is_active.is_(True)).count()

    # Load subscriptions with plans eagerly to avoid N+1 queries
    sub_query = db.query(Subscription).options(joinedload(Subscription.plan))
    if customer_id is not None:
        sub_query = sub_query.filter(Subscription.customer_id == customer_id)
    subscriptions = sub_query.all()

    total_subscriptions = len(subscriptions)
    active_subscriptions = 0
    mrr = Decimal("0.00")
    state_counts: Dict[str, int] = defaultdict(int)
    interval_stats: Dict[str, Dict] = defaultdict(
        lambda: {"count": 0, "mrr": Decimal("0.00")}
    )

    for sub in subscriptions:
        state_counts[sub.state] += 1
        if sub.state in ("active", "past_due"):
            active_subscriptions += 1
            interval = sub.plan.billing_interval if sub.plan else "monthly"
            net_recurring = max(
                Decimal("0.00"), sub.recurring_subtotal - sub.recurring_discount
            )
            sub_mrr = _normalize_to_mrr(net_recurring, interval)
            mrr = quantize_money(mrr + sub_mrr)
            interval_stats[interval]["count"] += 1
            interval_stats[interval]["mrr"] = quantize_money(
                interval_stats[interval]["mrr"] + sub_mrr
            )

    arr = quantize_money(mrr * Decimal("12.00"))

    # Invoices query
    inv_query = db.query(Invoice)
    if customer_id is not None:
        inv_query = inv_query.filter(Invoice.customer_id == customer_id)
    if date_from is not None:
        inv_query = inv_query.filter(Invoice.issue_date >= date_from)
    if date_to is not None:
        inv_query = inv_query.filter(Invoice.issue_date <= date_to)
    invoices = inv_query.all()

    billed_revenue = Decimal("0.00")
    billed_net_ex_tax = Decimal("0.00")
    recognized_total = Decimal("0.00")
    deferred_total = Decimal("0.00")
    outstanding_receivables = Decimal("0.00")
    overdue_count = 0
    overdue_amount = Decimal("0.00")

    trend_buckets: Dict[str, Dict[str, Decimal]] = defaultdict(
        lambda: {
            "billed": Decimal("0.00"),
            "collected": Decimal("0.00"),
            "recognized": Decimal("0.00"),
        }
    )

    ref_today = date.today()
    for inv in invoices:
        if inv.state in ("confirmed", "paid"):
            billed_revenue = quantize_money(billed_revenue + inv.total)
            net_ex_tax = quantize_money(
                max(Decimal("0.00"), inv.subtotal - inv.discount_amount)
            )
            billed_net_ex_tax = quantize_money(billed_net_ex_tax + net_ex_tax)

            rec, defe = _compute_pro_rata_recognition(
                net_ex_tax,
                inv.billing_period_start,
                inv.billing_period_end,
                today,
            )
            recognized_total = quantize_money(recognized_total + rec)
            deferred_total = quantize_money(deferred_total + defe)

            period_key = inv.issue_date.strftime("%Y-%m")
            trend_buckets[period_key]["billed"] = quantize_money(
                trend_buckets[period_key]["billed"] + inv.total
            )
            trend_buckets[period_key]["recognized"] = quantize_money(
                trend_buckets[period_key]["recognized"] + rec
            )

            if inv.amount_due > Decimal("0.00"):
                outstanding_receivables = quantize_money(
                    outstanding_receivables + inv.amount_due
                )
                if inv.due_date < ref_today:
                    overdue_count += 1
                    overdue_amount = quantize_money(overdue_amount + inv.amount_due)

    # Payments query
    pay_query = db.query(Payment).filter(Payment.status == "succeeded")
    if customer_id is not None:
        pay_query = pay_query.filter(Payment.customer_id == customer_id)
    if date_from is not None:
        pay_query = pay_query.filter(Payment.payment_date >= date_from)
    if date_to is not None:
        pay_query = pay_query.filter(Payment.payment_date <= date_to)
    payments = pay_query.all()

    cash_collected = Decimal("0.00")
    for p in payments:
        cash_collected = quantize_money(cash_collected + p.amount)
        period_key = p.payment_date.strftime("%Y-%m")
        trend_buckets[period_key]["collected"] = quantize_money(
            trend_buckets[period_key]["collected"] + p.amount
        )

    state_distribution = [
        StateDistributionItem(state=st, count=cnt)
        for st, cnt in sorted(state_counts.items())
    ]
    plan_distribution = [
        PlanDistributionItem(
            billing_interval=iv,
            count=data["count"],
            mrr_contribution=data["mrr"],
        )
        for iv, data in sorted(interval_stats.items())
    ]
    revenue_trends = [
        RevenueTrendItem(
            period=period,
            billed_revenue=vals["billed"],
            cash_collected=vals["collected"],
            recognized_revenue=vals["recognized"],
        )
        for period, vals in sorted(trend_buckets.items())
    ]

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return DashboardSummaryResponse(
        total_customers=total_customers,
        active_customers=active_customers,
        total_subscriptions=total_subscriptions,
        active_subscriptions=active_subscriptions,
        monthly_recurring_revenue=mrr,
        annual_recurring_revenue=arr,
        billed_revenue=billed_revenue,
        billed_net_ex_tax=billed_net_ex_tax,
        cash_collected=cash_collected,
        recognized_revenue_pro_rata=recognized_total,
        deferred_revenue_unearned=deferred_total,
        outstanding_receivables=outstanding_receivables,
        overdue_invoices_count=overdue_count,
        overdue_amount=overdue_amount,
        subscription_state_distribution=state_distribution,
        plan_interval_distribution=plan_distribution,
        revenue_trends=revenue_trends,
        query_execution_ms=elapsed_ms,
    )


def get_overdue_report(
    db: Session, customer_id: Optional[int] = None
) -> List[OverdueInvoiceItem]:
    today = date.today()
    query = (
        db.query(Invoice)
        .options(joinedload(Invoice.customer), joinedload(Invoice.subscription))
        .filter(
            Invoice.state == "confirmed",
            Invoice.amount_due > Decimal("0.00"),
            Invoice.due_date < today,
        )
    )
    if customer_id is not None:
        query = query.filter(Invoice.customer_id == customer_id)

    rows = query.order_by(Invoice.due_date.asc()).all()
    items = []
    for inv in rows:
        days_overdue = (today - inv.due_date).days
        items.append(
            OverdueInvoiceItem(
                invoice_id=inv.id,
                invoice_number=inv.invoice_number,
                subscription_id=inv.subscription_id,
                subscription_number=inv.subscription.subscription_number if inv.subscription else None,
                customer_id=inv.customer_id,
                customer_name=inv.customer.name if inv.customer else "Unknown",
                customer_email=inv.customer.email if inv.customer else "",
                issue_date=inv.issue_date,
                due_date=inv.due_date,
                days_overdue=days_overdue,
                total=inv.total,
                amount_paid=inv.amount_paid,
                amount_due=inv.amount_due,
            )
        )
    return items


def list_recent_audit_logs(db: Session, limit: int = 100) -> List[AuditLog]:
    return (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .all()
    )

