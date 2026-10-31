"""Deterministic Decimal financial calculations, tax resolution, discount validation, and billing period math."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple

from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Discount, Product, ProductVariant, TaxRule

TWOPLACES = Decimal("0.01")
HUNDRED = Decimal("100.00")


def quantize_money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def compute_billing_period(period_start: date, billing_interval: str) -> Tuple[date, date, date]:
    """Return (billing_period_start, billing_period_end, next_billing_date) for an interval."""
    if billing_interval == "daily":
        next_date = period_start + timedelta(days=1)
        period_end = period_start
    elif billing_interval == "weekly":
        next_date = period_start + timedelta(days=7)
        period_end = next_date - timedelta(days=1)
    elif billing_interval == "monthly":
        next_date = period_start + relativedelta(months=1)
        period_end = next_date - timedelta(days=1)
    elif billing_interval == "yearly":
        next_date = period_start + relativedelta(years=1)
        period_end = next_date - timedelta(days=1)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported billing interval: {billing_interval}",
        )
    return period_start, period_end, next_date


def resolve_tax_rate(
    db: Session,
    tax_rule_id: Optional[int],
    explicit_tax_rate: Optional[Decimal],
    reference_date: date,
) -> Tuple[Optional[int], Decimal]:
    """Resolve configurable tax rate from TaxRule table without hardcoded rates."""
    if tax_rule_id is not None:
        rule = db.query(TaxRule).filter(TaxRule.id == tax_rule_id).first()
        if not rule or not rule.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected tax rule is inactive or does not exist.",
            )
        if rule.effective_from and reference_date < rule.effective_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tax rule '{rule.name}' is not effective until {rule.effective_from}.",
            )
        if rule.effective_until and reference_date > rule.effective_until:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tax rule '{rule.name}' expired on {rule.effective_until}.",
            )
        return rule.id, quantize_money(rule.rate)

    if explicit_tax_rate is not None:
        rate = quantize_money(explicit_tax_rate)
        if rate < Decimal("0.00") or rate > HUNDRED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tax rate must be between 0 and 100.",
            )
        return None, rate

    default_rule = (
        db.query(TaxRule)
        .filter(TaxRule.is_active.is_(True), TaxRule.is_default.is_(True))
        .first()
    )
    if default_rule:
        if (not default_rule.effective_from or reference_date >= default_rule.effective_from) and (
            not default_rule.effective_until or reference_date <= default_rule.effective_until
        ):
            return default_rule.id, quantize_money(default_rule.rate)

    return None, Decimal("0.00")


def resolve_product_and_variant_price(
    db: Session,
    product_id: int,
    variant_id: Optional[int],
    override_unit_price: Optional[Decimal] = None,
) -> Tuple[Product, Optional[ProductVariant], Decimal, str]:
    """Resolve product, optional variant, unit_price (sales_price + price_extra), and line description."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product ID {product_id} not found.",
        )
    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product '{product.name}' is inactive and cannot be added to new orders.",
        )

    variant = None
    extra = Decimal("0.00")
    description = product.name

    if variant_id is not None:
        variant = (
            db.query(ProductVariant)
            .filter(
                ProductVariant.id == variant_id,
                ProductVariant.product_id == product.id,
            )
            .first()
        )
        if not variant or not variant.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product variant ID {variant_id} is invalid or inactive for product '{product.name}'.",
            )
        extra = quantize_money(variant.price_extra)
        description = f"{product.name} ({variant.name})"

    if override_unit_price is not None:
        unit_price = quantize_money(override_unit_price)
        if unit_price < Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unit price cannot be negative.",
            )
    else:
        unit_price = quantize_money(product.sales_price + extra)

    return product, variant, unit_price, description


def validate_and_calculate_discount(
    db: Session,
    discount_id: Optional[int],
    discount_code: Optional[str],
    lines_data: List[Dict],
    reference_date: date,
    consume_usage: bool = False,
) -> Tuple[Optional[Discount], Decimal]:
    """Validate discount eligibility (dates, usage limits, minimum purchase/qty, product scope)
    and return (Discount, discount_amount).
    """
    if not discount_id and not discount_code:
        return None, Decimal("0.00")

    query = db.query(Discount)
    if discount_id:
        discount = query.filter(Discount.id == discount_id).first()
    else:
        discount = query.filter(Discount.code == discount_code.strip().upper()).first()

    if not discount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specified discount does not exist.",
        )
    if not discount.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Discount '{discount.code}' is inactive.",
        )
    if discount.start_date and reference_date < discount.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Discount '{discount.code}' is not valid before {discount.start_date}.",
        )
    if discount.end_date and reference_date > discount.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Discount '{discount.code}' expired on {discount.end_date}.",
        )
    if discount.usage_limit is not None and discount.usage_count >= discount.usage_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Discount '{discount.code}' has reached its maximum usage limit ({discount.usage_limit}).",
        )

    subtotal = sum((item["line_subtotal"] for item in lines_data), Decimal("0.00"))
    total_qty = sum((int(item["quantity"]) for item in lines_data), 0)

    if subtotal < discount.min_purchase_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Discount '{discount.code}' requires a minimum purchase subtotal of "
                f"{discount.min_purchase_amount} (current subtotal: {subtotal})."
            ),
        )
    if total_qty < discount.min_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Discount '{discount.code}' requires a minimum quantity of "
                f"{discount.min_quantity} (current quantity: {total_qty})."
            ),
        )

    if discount.product_id is not None:
        eligible_subtotal = sum(
            (
                item["line_subtotal"]
                for item in lines_data
                if item["product_id"] == discount.product_id
            ),
            Decimal("0.00"),
        )
        if eligible_subtotal <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Discount '{discount.code}' only applies to product ID {discount.product_id}.",
            )
    else:
        eligible_subtotal = subtotal

    if discount.discount_type == "percentage":
        raw_discount = (eligible_subtotal * discount.value) / HUNDRED
        discount_amount = min(eligible_subtotal, quantize_money(raw_discount))
    else:
        discount_amount = min(eligible_subtotal, quantize_money(discount.value))

    if consume_usage:
        discount.usage_count += 1

    return discount, discount_amount


def calculate_order_totals(
    db: Session,
    raw_lines: List[Dict],
    reference_date: date,
    discount_id: Optional[int] = None,
    discount_code: Optional[str] = None,
    consume_discount: bool = False,
) -> Dict:
    """Compute line snapshots, subtotal, discount, proportional post-discount tax, and grand total."""
    if not raw_lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one line item is required.",
        )

    prepared_lines = []
    for item in raw_lines:
        qty = int(item["quantity"])
        if qty <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Line item quantity must be greater than zero.",
            )
        product, variant, unit_price, auto_desc = resolve_product_and_variant_price(
            db,
            product_id=item["product_id"],
            variant_id=item.get("variant_id"),
            override_unit_price=item.get("unit_price"),
        )
        resolved_rule_id, tax_rate = resolve_tax_rate(
            db,
            tax_rule_id=item.get("tax_rule_id"),
            explicit_tax_rate=item.get("tax_rate"),
            reference_date=reference_date,
        )
        line_subtotal = quantize_money(unit_price * Decimal(qty))
        prepared_lines.append(
            {
                "product_id": product.id,
                "variant_id": variant.id if variant else None,
                "tax_rule_id": resolved_rule_id,
                "description": item.get("description") or auto_desc,
                "quantity": qty,
                "unit_price": unit_price,
                "tax_rate": tax_rate,
                "line_subtotal": line_subtotal,
            }
        )

    subtotal = quantize_money(sum((l["line_subtotal"] for l in prepared_lines), Decimal("0.00")))
    discount_obj, discount_amount = validate_and_calculate_discount(
        db,
        discount_id=discount_id,
        discount_code=discount_code,
        lines_data=prepared_lines,
        reference_date=reference_date,
        consume_usage=consume_discount,
    )

    # Calculate line tax and line totals (accounting for discount proportionally across taxable base)
    tax_amount = Decimal("0.00")
    for line in prepared_lines:
        if subtotal > Decimal("0.00") and discount_amount > Decimal("0.00"):
            line_discount_share = quantize_money(
                (line["line_subtotal"] / subtotal) * discount_amount
            )
        else:
            line_discount_share = Decimal("0.00")
        taxable_base = max(Decimal("0.00"), line["line_subtotal"] - line_discount_share)
        line_tax = quantize_money((taxable_base * line["tax_rate"]) / HUNDRED)
        line["line_tax"] = line_tax
        line["line_total"] = quantize_money(line["line_subtotal"] + line_tax)
        tax_amount = quantize_money(tax_amount + line_tax)

    total = quantize_money(max(Decimal("0.00"), subtotal - discount_amount) + tax_amount)
    return {
        "lines": prepared_lines,
        "subtotal": subtotal,
        "discount": discount_obj,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "total": total,
    }

