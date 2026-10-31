"""Pydantic schemas for invoices, billing jobs, tax rules, and discounts."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TaxRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    rate: Decimal = Field(..., ge=Decimal("0.00"), le=Decimal("100.00"))
    region: str = Field(default="Global", max_length=128)
    category: str = Field(default="Standard", max_length=128)
    effective_from: Optional[date] = None
    effective_until: Optional[date] = None
    is_default: bool = False
    is_active: bool = True


class TaxRuleUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    rate: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    region: Optional[str] = None
    category: Optional[str] = None
    effective_from: Optional[date] = None
    effective_until: Optional[date] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class TaxRuleResponse(BaseModel):
    id: int
    name: str
    code: str
    rate: Decimal
    region: str
    category: str
    effective_from: Optional[date] = None
    effective_until: Optional[date] = None
    is_default: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscountCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=64)
    discount_type: str = Field(default="percentage", pattern="^(fixed|percentage)$")
    value: Decimal = Field(..., gt=Decimal("0.00"))
    min_purchase_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    min_quantity: int = Field(default=0, ge=0)
    product_id: Optional[int] = None
    applicable_to: str = Field(default="all", pattern="^(all|subscription|product)$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    usage_limit: Optional[int] = Field(default=None, ge=1)
    is_active: bool = True


class DiscountUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    discount_type: Optional[str] = Field(default=None, pattern="^(fixed|percentage)$")
    value: Optional[Decimal] = Field(default=None, gt=Decimal("0.00"))
    min_purchase_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    min_quantity: Optional[int] = Field(default=None, ge=0)
    product_id: Optional[int] = None
    applicable_to: Optional[str] = Field(default=None, pattern="^(all|subscription|product)$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    usage_limit: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class DiscountResponse(BaseModel):
    id: int
    name: str
    code: str
    discount_type: str
    value: Decimal
    min_purchase_amount: Decimal
    min_quantity: int
    product_id: Optional[int] = None
    applicable_to: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    usage_limit: Optional[int] = None
    usage_count: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceLineResponse(BaseModel):
    id: int
    product_id: Optional[int] = None
    variant_id: Optional[int] = None
    tax_rule_id: Optional[int] = None
    description: str
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class InvoiceGenerateRequest(BaseModel):
    subscription_id: Optional[int] = Field(
        default=None,
        description="If provided, generates an invoice for this subscription; otherwise runs due billing batch",
    )
    billing_period_start: Optional[date] = Field(
        default=None,
        description="Optional explicit billing period start date",
    )
    target_date: Optional[date] = Field(
        default=None,
        description="Reference billing date when running automated billing detection",
    )
    auto_confirm: bool = Field(
        default=True,
        description="Whether to automatically confirm the generated invoice",
    )
    advance_next_billing_date: bool = Field(
        default=True,
        description="Whether to advance subscription.next_billing_date to the next period",
    )


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    subscription_id: int
    subscription_number: Optional[str] = None
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    discount_id: Optional[int] = None
    billing_period_start: date
    billing_period_end: date
    issue_date: date
    due_date: date
    state: str
    payment_status: str
    is_overdue: bool = False
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    notes: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    lines: List[InvoiceLineResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BillingRunSummaryResponse(BaseModel):
    target_date: date
    evaluated_subscriptions: int
    generated_count: int
    skipped_duplicates: int
    auto_closed_subscriptions: int
    invoices: List[InvoiceResponse] = Field(default_factory=list)

