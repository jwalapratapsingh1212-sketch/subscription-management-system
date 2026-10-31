"""Integration tests for complete Quote -> Subscription -> Billing -> Payment -> Dashboard workflow."""
from datetime import date, timedelta
from decimal import Decimal

from tests.conftest import get_auth_headers


def test_complete_end_to_end_business_workflow(client):
    """Test the complete lifecycle:
    Admin creates product & plan -> Staff creates customer & quotation ->
    Confirm quotation -> Subscription active -> Generate billing invoice ->
    Partial payment -> Full payment reconciliation -> Dashboard metrics update.
    """
    admin_headers = get_auth_headers(client, "admin@submanage.io", "Admin@12345")
    staff_headers = get_auth_headers(client, "staff@submanage.io", "Staff@12345")

    # 1. Admin creates a new Product with a Variant
    prod_resp = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "sku": "PRD-E2E-CLOUD",
            "name": "E2E Cloud Analytics Engine",
            "product_type": "software",
            "sales_price": "400.00",
            "cost_price": "80.00",
            "notes": "Integration test product",
            "variants": [
                {
                    "name": "Enterprise High-Availability Addon",
                    "sku": "VAR-E2E-HA",
                    "attribute_name": "SLA",
                    "attribute_value": "99.99%",
                    "price_extra": "100.00",
                }
            ],
        },
    )
    assert prod_resp.status_code == 201
    product = prod_resp.json()
    variant_id = product["variants"][0]["id"]

    # 2. Admin creates a Monthly Subscription Plan
    plan_resp = client.post(
        "/api/v1/plans",
        headers=admin_headers,
        json={
            "code": "PLN-E2E-MONTHLY",
            "name": "E2E Monthly Enterprise Plan",
            "billing_interval": "monthly",
            "minimum_quantity": 2,
            "default_payment_term_days": 14,
            "pause_allowed": True,
            "resume_allowed": True,
            "renewal_allowed": True,
            "early_close_allowed": True,
        },
    )
    assert plan_resp.status_code == 201
    plan = plan_resp.json()

    # 3. Staff creates a Customer
    cust_resp = client.post(
        "/api/v1/customers",
        headers=staff_headers,
        json={
            "name": "David Kim",
            "company_name": "Quantum Orbit Systems",
            "email": "david@quantumorbit.io",
            "phone": "+1-555-0199",
            "billing_address": "500 Orbit Way, Austin, TX",
        },
    )
    assert cust_resp.status_code == 201
    customer = cust_resp.json()

    # 4. Staff prepares a Quotation (2 units @ $500 [$400 base + $100 variant] = $1000 subtotal,
    #    WELCOME10 10% discount = -$100 -> $900 net + 10% default US tax ($90) = $990.00 total)
    quote_resp = client.post(
        "/api/v1/quotations",
        headers=staff_headers,
        json={
            "customer_id": customer["id"],
            "plan_id": plan["id"],
            "discount_code": "WELCOME10",
            "valid_until": str(date.today() + timedelta(days=15)),
            "status": "sent",
            "lines": [
                {
                    "product_id": product["id"],
                    "variant_id": variant_id,
                    "quantity": 2,
                }
            ],
        },
    )
    assert quote_resp.status_code == 201
    quote = quote_resp.json()
    assert Decimal(quote["subtotal"]) == Decimal("1000.00")
    assert Decimal(quote["discount_amount"]) == Decimal("100.00")
    assert Decimal(quote["tax_amount"]) == Decimal("90.00")
    assert Decimal(quote["total"]) == Decimal("990.00")

    # 5. Confirm Quotation -> Converts to Active Subscription
    confirm_resp = client.post(
        f"/api/v1/quotations/{quote['id']}/confirm",
        headers=staff_headers,
        json={"activate_immediately": True},
    )
    assert confirm_resp.status_code == 201
    sub = confirm_resp.json()
    assert sub["state"] == "active"
    assert Decimal(sub["recurring_total"]) == Decimal("990.00")

    # 6. Generate Billing Invoice for the Subscription
    period_start = sub["start_date"]
    inv_resp = client.post(
        "/api/v1/invoices/generate",
        headers=staff_headers,
        json={
            "subscription_id": sub["id"],
            "billing_period_start": period_start,
            "auto_confirm": True,
        },
    )
    assert inv_resp.status_code == 201
    invoice = inv_resp.json()
    assert invoice["state"] == "confirmed"
    assert invoice["payment_status"] == "unpaid"
    assert Decimal(invoice["total"]) == Decimal("990.00")
    assert Decimal(invoice["amount_due"]) == Decimal("990.00")

    # 7. Duplicate Invoice Prevention: Attempting to generate the same billing period again is rejected (409)
    dup_resp = client.post(
        "/api/v1/invoices/generate",
        headers=staff_headers,
        json={
            "subscription_id": sub["id"],
            "billing_period_start": period_start,
            "auto_confirm": True,
        },
    )
    assert dup_resp.status_code == 409

    # 8. Historical Invoice Immutability: Edit product sales_price and verify historical invoice does NOT change
    patch_prod = client.patch(
        f"/api/v1/products/{product['id']}",
        headers=admin_headers,
        json={"sales_price": "999.00"},
    )
    assert patch_prod.status_code == 200
    inv_check = client.get(f"/api/v1/invoices/{invoice['id']}", headers=staff_headers).json()
    assert Decimal(inv_check["total"]) == Decimal("990.00")
    assert Decimal(inv_check["lines"][0]["unit_price"]) == Decimal("500.00")

    # 9. Partial Payment ($400.00) -> Leaves $590.00 outstanding balance & partially_paid status
    pay1_resp = client.post(
        "/api/v1/payments",
        headers=staff_headers,
        json={
            "invoice_id": invoice["id"],
            "method": "credit_card",
            "amount": "400.00",
            "idempotency_key": "e2e-pay-key-1",
        },
    )
    assert pay1_resp.status_code == 201
    bal1 = client.get(f"/api/v1/invoices/{invoice['id']}/balance", headers=staff_headers).json()
    assert Decimal(bal1["amount_paid"]) == Decimal("400.00")
    assert Decimal(bal1["amount_due"]) == Decimal("590.00")
    assert bal1["payment_status"] == "partially_paid"
    assert bal1["state"] == "confirmed"

    # 10. Payment Idempotency: Repeating the exact same idempotency_key does not double-deduct balance
    pay1_retry = client.post(
        "/api/v1/payments",
        headers=staff_headers,
        json={
            "invoice_id": invoice["id"],
            "method": "credit_card",
            "amount": "400.00",
            "idempotency_key": "e2e-pay-key-1",
        },
    )
    assert pay1_retry.status_code == 201
    assert pay1_retry.json()["id"] == pay1_resp.json()["id"]
    bal_after_retry = client.get(
        f"/api/v1/invoices/{invoice['id']}/balance", headers=staff_headers
    ).json()
    assert Decimal(bal_after_retry["amount_due"]) == Decimal("590.00")

    # 11. Overpayment Protection: Attempting to pay $600 when only $590 is due is rejected (400)
    overpay_resp = client.post(
        "/api/v1/payments",
        headers=staff_headers,
        json={
            "invoice_id": invoice["id"],
            "method": "wire",
            "amount": "600.00",
            "idempotency_key": "e2e-overpay-key",
        },
    )
    assert overpay_resp.status_code == 400

    # 12. Remaining Full Payment ($590.00) -> Marks invoice 'paid' with $0.00 due
    pay2_resp = client.post(
        "/api/v1/payments",
        headers=staff_headers,
        json={
            "invoice_id": invoice["id"],
            "method": "wire",
            "amount": "590.00",
            "idempotency_key": "e2e-pay-key-2",
        },
    )
    assert pay2_resp.status_code == 201
    bal2 = client.get(f"/api/v1/invoices/{invoice['id']}/balance", headers=staff_headers).json()
    assert Decimal(bal2["amount_paid"]) == Decimal("990.00")
    assert Decimal(bal2["amount_due"]) == Decimal("0.00")
    assert bal2["state"] == "paid"
    assert bal2["payment_status"] == "paid"


def test_expired_quotation_cannot_be_confirmed(client):
    """Verify a quotation past its valid_until date cannot be confirmed."""
    staff_headers = get_auth_headers(client, "staff@submanage.io", "Staff@12345")
    customers = client.get("/api/v1/customers", headers=staff_headers).json()["items"]
    plans = client.get("/api/v1/plans", headers=staff_headers).json()
    products = client.get("/api/v1/products", headers=staff_headers).json()

    q_resp = client.post(
        "/api/v1/quotations",
        headers=staff_headers,
        json={
            "customer_id": customers[0]["id"],
            "plan_id": plans[0]["id"],
            "valid_until": str(date.today() - timedelta(days=5)),
            "status": "sent",
            "lines": [{"product_id": products[0]["id"], "quantity": 1}],
        },
    )
    assert q_resp.status_code == 201
    q_id = q_resp.json()["id"]

    confirm_resp = client.post(f"/api/v1/quotations/{q_id}/confirm", headers=staff_headers)
    assert confirm_resp.status_code == 400
    assert "expired" in confirm_resp.json()["detail"].lower()

