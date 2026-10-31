"""Unit tests for password policy, billing period calculation, tax arithmetic, discount eligibility, and state machine."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi import HTTPException

from app.core.financials import (
    calculate_order_totals,
    compute_billing_period,
    quantize_money,
    validate_and_calculate_discount,
)
from app.core.security import (
    create_jwt_token,
    decode_jwt_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.models import Discount, Product
from app.reports.service import _compute_pro_rata_recognition
from app.subscriptions.service import ALLOWED_SUBSCRIPTION_TRANSITIONS


def test_password_policy_enforcement():
    """Verify password policy rejects weak passwords and accepts compliant passwords."""
    # Too short
    with pytest.raises(HTTPException) as exc:
        validate_password_strength("Ab1!xy")
    assert exc.value.status_code == 400

    # Missing uppercase
    with pytest.raises(HTTPException):
        validate_password_strength("lowercase123!@#")

    # Missing lowercase
    with pytest.raises(HTTPException):
        validate_password_strength("UPPERCASE123!@#")

    # Missing special character
    with pytest.raises(HTTPException):
        validate_password_strength("NoSpecialChar123")

    # Valid strong password
    validate_password_strength("StrongPass#2026")
    hashed = hash_password("StrongPass#2026")
    assert hashed != "StrongPass#2026"
    assert verify_password("StrongPass#2026", hashed) is True
    assert verify_password("WrongPass#2026", hashed) is False


def test_jwt_encode_and_decode():
    token = create_jwt_token(
        subject=99,
        email="unit@test.io",
        role="staff",
        customer_id=None,
        token_type="access",
    )
    decoded = decode_jwt_token(token, expected_type="access")
    assert decoded["sub"] == "99"
    assert decoded["email"] == "unit@test.io"
    assert decoded["role"] == "staff"


def test_billing_period_calculations_across_intervals():
    """Verify daily, weekly, monthly, and yearly billing period date arithmetic."""
    start = date(2026, 1, 15)

    # Daily
    p_start, p_end, next_dt = compute_billing_period(start, "daily")
    assert p_start == date(2026, 1, 15)
    assert p_end == date(2026, 1, 15)
    assert next_dt == date(2026, 1, 16)

    # Weekly
    p_start, p_end, next_dt = compute_billing_period(start, "weekly")
    assert p_start == date(2026, 1, 15)
    assert p_end == date(2026, 1, 21)
    assert next_dt == date(2026, 1, 22)

    # Monthly (including month-end boundary Jan 31 -> Feb 28)
    jan_end = date(2026, 1, 31)
    p_start, p_end, next_dt = compute_billing_period(jan_end, "monthly")
    assert p_start == date(2026, 1, 31)
    assert next_dt == date(2026, 2, 28)
    assert p_end == date(2026, 2, 27)

    # Yearly
    p_start, p_end, next_dt = compute_billing_period(start, "yearly")
    assert p_start == date(2026, 1, 15)
    assert next_dt == date(2027, 1, 15)
    assert p_end == date(2027, 1, 14)


def test_discount_eligibility_dates_and_usage_limits(db_session):
    """Verify discounts outside effective dates, below minimum purchase, or over usage limit are rejected."""
    today = date.today()
    expired_disc = Discount(
        name="Expired Promo",
        code="EXPIRED99",
        discount_type="fixed",
        value=Decimal("50.00"),
        min_purchase_amount=Decimal("100.00"),
        min_quantity=1,
        start_date=today - timedelta(days=30),
        end_date=today - timedelta(days=1),
        usage_limit=10,
        usage_count=0,
        is_active=True,
    )
    maxed_disc = Discount(
        name="Maxed Out Promo",
        code="MAXED99",
        discount_type="percentage",
        value=Decimal("20.00"),
        min_purchase_amount=Decimal("50.00"),
        min_quantity=1,
        usage_limit=5,
        usage_count=5,
        is_active=True,
    )
    db_session.add_all([expired_disc, maxed_disc])
    db_session.commit()

    sample_lines = [{"product_id": 1, "quantity": 2, "line_subtotal": Decimal("300.00")}]

    # Expired discount rejected
    with pytest.raises(HTTPException) as exc1:
        validate_and_calculate_discount(
            db_session, expired_disc.id, None, sample_lines, today
        )
    assert "expired" in exc1.value.detail.lower()

    # Usage limit reached rejected
    with pytest.raises(HTTPException) as exc2:
        validate_and_calculate_discount(
            db_session, maxed_disc.id, None, sample_lines, today
        )
    assert "usage limit" in exc2.value.detail.lower()


def test_decimal_order_totals_and_tax_arithmetic(db_session):
    """Verify exact Decimal subtotal, discount, proportional tax, and grand total."""
    prod = db_session.query(Product).first()
    calc = calculate_order_totals(
        db_session,
        raw_lines=[
            {
                "product_id": prod.id,
                "quantity": 2,
                "unit_price": Decimal("250.00"),
                "tax_rate": Decimal("10.00"),
            }
        ],
        reference_date=date.today(),
        discount_code="WELCOME10",  # 10% off
    )
    assert calc["subtotal"] == Decimal("500.00")
    assert calc["discount_amount"] == Decimal("50.00")
    # Taxable base after 10% discount = 450.00 -> 10% tax = 45.00
    assert calc["tax_amount"] == Decimal("45.00")
    assert calc["total"] == Decimal("495.00")
    assert isinstance(calc["total"], Decimal)


def test_subscription_state_machine_matrix():
    """Verify allowed vs disallowed state transitions."""
    assert "quotation" in ALLOWED_SUBSCRIPTION_TRANSITIONS["draft"]
    assert "confirmed" in ALLOWED_SUBSCRIPTION_TRANSITIONS["quotation"]
    assert "active" in ALLOWED_SUBSCRIPTION_TRANSITIONS["confirmed"]
    assert "paused" in ALLOWED_SUBSCRIPTION_TRANSITIONS["active"]
    assert "active" in ALLOWED_SUBSCRIPTION_TRANSITIONS["paused"]
    assert "closed" in ALLOWED_SUBSCRIPTION_TRANSITIONS["active"]
    assert len(ALLOWED_SUBSCRIPTION_TRANSITIONS["closed"]) == 0


def test_pro_rata_revenue_recognition():
    """Verify ASC 606 preview pro-rata recognition splits earned vs deferred revenue accurately."""
    start = date(2026, 1, 1)
    end = date(2026, 1, 30)  # 30 days inclusive
    mid = date(2026, 1, 15)  # 15 days elapsed (50%)
    rec, defe = _compute_pro_rata_recognition(Decimal("600.00"), start, end, mid)
    assert rec == Decimal("300.00")
    assert defe == Decimal("300.00")
    assert quantize_money(rec + defe) == Decimal("600.00")

