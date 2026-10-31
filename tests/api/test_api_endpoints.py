"""API & Performance tests across Auth, Catalog, Subscriptions, Invoices, Reports, and PDF/Print."""
from decimal import Decimal

from tests.conftest import get_auth_headers


def test_password_reset_flow(client):
    """Verify self-service forgot-password and reset-password flow."""
    forgot_resp = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "bob@globalfintech.io"},
    )
    assert forgot_resp.status_code == 200
    reset_token = forgot_resp.json()["reset_token"]
    assert reset_token is not None

    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={
            "reset_token": reset_token,
            "new_password": "NewPassword#2026",
        },
    )
    assert reset_resp.status_code == 200

    # Verify login works with new password
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@globalfintech.io", "password": "NewPassword#2026"},
    )
    assert login_resp.status_code == 200


def test_subscription_lifecycle_pause_resume_renew_close_and_invalid_transitions(client):
    """Verify valid and invalid subscription state transitions via API."""
    staff_headers = get_auth_headers(client, "staff@submanage.io", "Staff@12345")
    customers = client.get("/api/v1/customers", headers=staff_headers).json()["items"]
    plans = client.get("/api/v1/plans", headers=staff_headers).json()
    monthly_plan = next(p for p in plans if p["billing_interval"] == "monthly")
    products = client.get("/api/v1/products", headers=staff_headers).json()

    # Create in draft state
    sub_resp = client.post(
        "/api/v1/subscriptions",
        headers=staff_headers,
        json={
            "customer_id": customers[0]["id"],
            "plan_id": monthly_plan["id"],
            "initial_state": "draft",
            "lines": [{"product_id": products[0]["id"], "quantity": 1}],
        },
    )
    assert sub_resp.status_code == 201
    sub_id = sub_resp.json()["id"]

    # Invalid transition: cannot pause a draft subscription
    bad_pause = client.post(f"/api/v1/subscriptions/{sub_id}/pause", headers=staff_headers)
    assert bad_pause.status_code == 400

    # Valid transition: draft -> quotation -> confirmed -> active -> paused -> active -> renew -> close
    r1 = client.post(f"/api/v1/subscriptions/{sub_id}/send-quote", headers=staff_headers)
    assert r1.status_code == 200 and r1.json()["state"] == "quotation"

    r2 = client.post(f"/api/v1/subscriptions/{sub_id}/confirm", headers=staff_headers)
    assert r2.status_code == 200 and r2.json()["state"] == "confirmed"

    r3 = client.post(f"/api/v1/subscriptions/{sub_id}/activate", headers=staff_headers)
    assert r3.status_code == 200 and r3.json()["state"] == "active"

    r4 = client.post(f"/api/v1/subscriptions/{sub_id}/pause", headers=staff_headers)
    assert r4.status_code == 200 and r4.json()["state"] == "paused"

    r5 = client.post(f"/api/v1/subscriptions/{sub_id}/resume", headers=staff_headers)
    assert r5.status_code == 200 and r5.json()["state"] == "active"

    r6 = client.post(f"/api/v1/subscriptions/{sub_id}/renew", headers=staff_headers)
    assert r6.status_code == 200 and r6.json()["state"] == "active"

    r7 = client.post(f"/api/v1/subscriptions/{sub_id}/close", headers=staff_headers)
    assert r7.status_code == 200 and r7.json()["state"] == "closed"


def test_invoice_print_html_and_pdf_export(client):
    """Verify invoice HTML print view and PDF binary generation."""
    staff_headers = get_auth_headers(client, "staff@submanage.io", "Staff@12345")
    invoices = client.get("/api/v1/invoices", headers=staff_headers).json()
    inv_id = invoices[0]["id"]

    html_resp = client.get(f"/api/v1/invoices/{inv_id}/print", headers=staff_headers)
    assert html_resp.status_code == 200
    assert "INVOICE" in html_resp.text

    pdf_resp = client.get(f"/api/v1/invoices/{inv_id}/pdf", headers=staff_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF-1.4")


def test_dashboard_and_overdue_reporting_performance(client):
    """Verify Finance Dashboard & Overdue queries execute well under the 2000ms target."""
    staff_headers = get_auth_headers(client, "staff@submanage.io", "Staff@12345")

    dash_resp = client.get("/api/v1/reports/dashboard", headers=staff_headers)
    assert dash_resp.status_code == 200
    data = dash_resp.json()
    assert data["query_execution_ms"] < 2000.0
    assert Decimal(data["billed_revenue"]) > Decimal("0.00")
    assert Decimal(data["cash_collected"]) > Decimal("0.00")
    assert "recognized_revenue_pro_rata" in data
    assert "deferred_revenue_unearned" in data

    overdue_resp = client.get("/api/v1/reports/overdue", headers=staff_headers)
    assert overdue_resp.status_code == 200
    overdue_items = overdue_resp.json()
    assert len(overdue_items) >= 1
    assert overdue_items[0]["days_overdue"] > 0

