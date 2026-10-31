"""Pydantic schemas for quotation templates, quotations, and subscriptions."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class OrderLineInput(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    tax_rule_id: Optional[int] = None
    description: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    unit_price: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    tax_rate: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))


class OrderLineResponse(BaseModel):
    id: int
    product_id: int
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


class QuotationTemplateCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    plan_id: int
    validity_days: int = Field(default=30, ge=1)
    payment_terms: str = Field(default="Net 14", max_length=128)
    notes: Optional[str] = None
    default_lines: List[OrderLineInput] = Field(default_factory=list)
    is_active: bool = True


class QuotationTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    plan_id: int
    validity_days: int
    payment_terms: str
    notes: Optional[str] = None
    default_lines_json: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuotationCreateRequest(BaseModel):
    customer_id: int
    plan_id: int
    template_id: Optional[int] = None
    discount_id: Optional[int] = None
    discount_code: Optional[str] = None
    valid_until: Optional[date] = None
    start_date: Optional[date] = None
    payment_terms: str = Field(default="Net 14", max_length=128)
    notes: Optional[str] = None
    status: str = Field(default="draft", pattern="^(draft|sent)$")
    lines: List[OrderLineInput] = Field(default_factory=list)


class QuotationUpdateRequest(BaseModel):
    valid_until: Optional[date] = None
    start_date: Optional[date] = None
    payment_terms: Optional[str] = None
    discount_id: Optional[int] = None
    discount_code: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(draft|sent|cancelled)$")
    lines: Optional[List[OrderLineInput]] = None


class QuotationConfirmRequest(BaseModel):
    activate_immediately: bool = True
    start_date: Optional[date] = None


class QuotationResponse(BaseModel):
    id: int
    quotation_number: str
    customer_id: int
    customer_name: Optional[str] = None
    plan_id: int
    plan_name: Optional[str] = None
    template_id: Optional[int] = None
    discount_id: Optional[int] = None
    status: str
    valid_until: date
    start_date: Optional[date] = None
    payment_terms: str
    notes: Optional[str] = None
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total: Decimal
    lines: List[OrderLineResponse] = Field(default_factory=list)
    subscription_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionCreateRequest(BaseModel):
    customer_id: int
    plan_id: int
    discount_id: Optional[int] = None
    discount_code: Optional[str] = None
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    payment_terms: str = Field(default="Net 14", max_length=128)
    payment_term_days: int = Field(default=14, ge=0)
    auto_renew: bool = True
    notes: Optional[str] = None
    initial_state: str = Field(
        default="draft", pattern="^(draft|quotation|confirmed|active)$"
    )
    lines: List[OrderLineInput] = Field(..., min_length=1)


class SubscriptionUpdateRequest(BaseModel):
    expiry_date: Optional[date] = None
    payment_terms: Optional[str] = None
    payment_term_days: Optional[int] = Field(default=None, ge=0)
    auto_renew: Optional[bool] = None
    notes: Optional[str] = None
    discount_id: Optional[int] = None
    lines: Optional[List[OrderLineInput]] = None


class SubscriptionResponse(BaseModel):
    id: int
    subscription_number: str
    customer_id: int
    customer_name: Optional[str] = None
    plan_id: int
    plan_name: Optional[str] = None
    billing_interval: Optional[str] = None
    quotation_id: Optional[int] = None
    discount_id: Optional[int] = None
    state: str
    start_date: date
    expiry_date: Optional[date] = None
    next_billing_date: Optional[date] = None
    paused_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    payment_terms: str
    payment_term_days: int
    auto_renew: bool
    notes: Optional[str] = None
    recurring_subtotal: Decimal
    recurring_discount: Decimal
    recurring_tax: Decimal
    recurring_total: Decimal
    lines: List[OrderLineResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

