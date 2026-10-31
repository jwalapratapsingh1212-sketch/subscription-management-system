"""Pydantic schemas for Finance Dashboard, Revenue Analytics, Overdue Aging, and Audit Logs."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StateDistributionItem(BaseModel):
    state: str
    count: int


class PlanDistributionItem(BaseModel):
    billing_interval: str
    count: int
    mrr_contribution: Decimal


class RevenueTrendItem(BaseModel):
    period: str
    billed_revenue: Decimal
    cash_collected: Decimal
    recognized_revenue: Decimal


class DashboardSummaryResponse(BaseModel):
    total_customers: int
    active_customers: int
    total_subscriptions: int
    active_subscriptions: int
    monthly_recurring_revenue: Decimal
    annual_recurring_revenue: Decimal
    # Explicitly separated revenue & cash metrics per Architecture Guide Section 6 & 10
    billed_revenue: Decimal
    billed_net_ex_tax: Decimal
    cash_collected: Decimal
    recognized_revenue_pro_rata: Decimal
    deferred_revenue_unearned: Decimal
    outstanding_receivables: Decimal
    overdue_invoices_count: int
    overdue_amount: Decimal
    subscription_state_distribution: List[StateDistributionItem] = Field(default_factory=list)
    plan_interval_distribution: List[PlanDistributionItem] = Field(default_factory=list)
    revenue_trends: List[RevenueTrendItem] = Field(default_factory=list)
    query_execution_ms: float = 0.0


class OverdueInvoiceItem(BaseModel):
    invoice_id: int
    invoice_number: str
    subscription_id: int
    subscription_number: Optional[str] = None
    customer_id: int
    customer_name: str
    customer_email: str
    issue_date: date
    due_date: date
    days_overdue: int
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal


class AuditLogResponse(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    actor_email: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    timestamp: datetime
    metadata_json: str

    model_config = ConfigDict(from_attributes=True)

