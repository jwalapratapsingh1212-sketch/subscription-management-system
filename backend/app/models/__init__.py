"""Normalized SQLAlchemy ORM models for the Subscription Management System."""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, DecimalMoney


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="customer", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reset_token: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    reset_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    customer_profile: Mapped[Optional["Customer"]] = relationship(
        "Customer", back_populates="user", uselist=False
    )

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'staff', 'customer')", name="ck_users_role"),
    )


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tax_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    billing_address: Mapped[str] = mapped_column(Text, nullable=False, default="")
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, default="US")
    postal_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    user: Mapped[Optional["User"]] = relationship("User", back_populates="customer_profile")
    quotations: Mapped[List["Quotation"]] = relationship("Quotation", back_populates="customer")
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="customer")
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="customer")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    product_type: Mapped[str] = mapped_column(String(64), nullable=False, default="service")
    sales_price: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    cost_price: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    variants: Mapped[List["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("sales_price >= 0", name="ck_products_sales_price_non_neg"),
        CheckConstraint("cost_price >= 0", name="ck_products_cost_price_non_neg"),
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    attribute_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    attribute_value: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    price_extra: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    product: Mapped["Product"] = relationship("Product", back_populates="variants")

    __table_args__ = (
        CheckConstraint("price_extra >= 0", name="ck_product_variants_price_extra_non_neg"),
    )


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    billing_interval: Mapped[str] = mapped_column(String(32), nullable=False, default="monthly")
    minimum_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    available_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    available_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    trial_period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    default_payment_term_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    auto_close: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    early_close_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pause_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    resume_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    renewal_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="plan")

    __table_args__ = (
        CheckConstraint(
            "billing_interval IN ('daily', 'weekly', 'monthly', 'yearly')",
            name="ck_plans_billing_interval",
        ),
        CheckConstraint("minimum_quantity >= 1", name="ck_plans_min_quantity_positive"),
    )


class TaxRule(Base):
    __tablename__ = "tax_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(
        DecimalMoney(5, 2), nullable=False, default=Decimal("0.00")
    )
    region: Mapped[str] = mapped_column(String(128), nullable=False, default="Global")
    category: Mapped[str] = mapped_column(String(128), nullable=False, default="Standard")
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint("rate >= 0 AND rate <= 100", name="ck_tax_rules_rate_bounds"),
    )


class Discount(Base):
    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    discount_type: Mapped[str] = mapped_column(String(32), nullable=False, default="percentage")
    value: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)
    min_purchase_amount: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    applicable_to: Mapped[str] = mapped_column(String(32), nullable=False, default="all")
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    usage_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    product: Mapped[Optional["Product"]] = relationship("Product")

    __table_args__ = (
        CheckConstraint(
            "discount_type IN ('fixed', 'percentage')", name="ck_discounts_type"
        ),
        CheckConstraint("value > 0", name="ck_discounts_value_positive"),
        CheckConstraint("min_purchase_amount >= 0", name="ck_discounts_min_purchase_non_neg"),
        CheckConstraint("min_quantity >= 0", name="ck_discounts_min_qty_non_neg"),
        CheckConstraint("usage_count >= 0", name="ck_discounts_usage_count_non_neg"),
    )


class QuotationTemplate(Base):
    __tablename__ = "quotation_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id"), nullable=False)
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    payment_terms: Mapped[str] = mapped_column(String(128), nullable=False, default="Net 14")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_lines_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    plan: Mapped["Plan"] = relationship("Plan")


class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quotation_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    template_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("quotation_templates.id", ondelete="SET NULL"), nullable=True
    )
    discount_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("discounts.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(128), nullable=False, default="Net 14")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    total: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="quotations")
    plan: Mapped["Plan"] = relationship("Plan")
    discount: Mapped[Optional["Discount"]] = relationship("Discount")
    lines: Mapped[List["QuotationLine"]] = relationship(
        "QuotationLine", back_populates="quotation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'sent', 'confirmed', 'expired', 'cancelled')",
            name="ck_quotations_status",
        ),
        CheckConstraint("total >= 0", name="ck_quotations_total_non_neg"),
    )


class QuotationLine(Base):
    __tablename__ = "quotation_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quotation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    tax_rule_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tax_rules.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(
        DecimalMoney(5, 2), nullable=False, default=Decimal("0.00")
    )
    line_subtotal: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)
    line_tax: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)

    quotation: Mapped["Quotation"] = relationship("Quotation", back_populates="lines")
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_quotation_lines_qty_positive"),
        CheckConstraint("unit_price >= 0", name="ck_quotation_lines_unit_price_non_neg"),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscription_number: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    quotation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True
    )
    discount_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("discounts.id", ondelete="SET NULL"), nullable=True
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_billing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(128), nullable=False, default="Net 14")
    payment_term_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recurring_subtotal: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    recurring_discount: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    recurring_tax: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    recurring_total: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship("Plan", back_populates="subscriptions")
    discount: Mapped[Optional["Discount"]] = relationship("Discount")
    lines: Mapped[List["SubscriptionLine"]] = relationship(
        "SubscriptionLine", back_populates="subscription", cascade="all, delete-orphan"
    )
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="subscription")

    __table_args__ = (
        CheckConstraint(
            "state IN ('draft', 'quotation', 'confirmed', 'active', 'paused', 'past_due', 'closed')",
            name="ck_subscriptions_state",
        ),
        Index("ix_subscriptions_state_next_billing", "state", "next_billing_date"),
    )


class SubscriptionLine(Base):
    __tablename__ = "subscription_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscription_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    tax_rule_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tax_rules.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(
        DecimalMoney(5, 2), nullable=False, default=Decimal("0.00")
    )
    line_subtotal: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)
    line_tax: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)

    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="lines")
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_subscription_lines_qty_positive"),
        CheckConstraint("unit_price >= 0", name="ck_subscription_lines_unit_price_non_neg"),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    subscription_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscriptions.id"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    discount_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("discounts.id", ondelete="SET NULL"), nullable=True
    )
    billing_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    billing_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    payment_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unpaid", index=True
    )
    subtotal: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    total: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    amount_paid: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    amount_due: Mapped[Decimal] = mapped_column(
        DecimalMoney(12, 2), nullable=False, default=Decimal("0.00")
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="invoices")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="invoices")
    discount: Mapped[Optional["Discount"]] = relationship("Discount")
    lines: Mapped[List["InvoiceLine"]] = relationship(
        "InvoiceLine", back_populates="invoice", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="invoice")

    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "billing_period_start",
            "billing_period_end",
            name="uq_invoice_subscription_billing_period",
        ),
        CheckConstraint(
            "state IN ('draft', 'confirmed', 'paid', 'cancelled')",
            name="ck_invoices_state",
        ),
        CheckConstraint(
            "payment_status IN ('unpaid', 'partially_paid', 'paid', 'overdue', 'cancelled')",
            name="ck_invoices_payment_status",
        ),
        CheckConstraint("total >= 0", name="ck_invoices_total_non_neg"),
        CheckConstraint("amount_paid >= 0", name="ck_invoices_amount_paid_non_neg"),
        CheckConstraint("amount_due >= 0", name="ck_invoices_amount_due_non_neg"),
        Index("ix_invoices_due_date_state", "due_date", "state"),
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    variant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    tax_rule_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tax_rules.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(
        DecimalMoney(5, 2), nullable=False, default=Decimal("0.00")
    )
    line_subtotal: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)
    line_tax: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="lines")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_invoice_lines_qty_positive"),
        CheckConstraint("unit_price >= 0", name="ck_invoice_lines_unit_price_non_neg"),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("invoices.id"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(String(64), nullable=False, default="credit_card")
    amount: Mapped[Decimal] = mapped_column(DecimalMoney(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="succeeded", index=True)
    recorded_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="payments")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint(
            "status IN ('succeeded', 'failed', 'refunded')", name="ck_payments_status"
        ),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class BillingJob(Base):
    __tablename__ = "billing_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscription_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    billing_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    billing_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    invoice_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "billing_period_start",
            "billing_period_end",
            name="uq_billing_job_sub_period",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_billing_jobs_status",
        ),
    )

