"""Security, RBAC, and Customer Isolation tests (per Architecture Guide Section 6 & 7)."""
from tests.conftest import get_auth_headers


def test_unauthenticated_access_denied(client):
    """Verify protected endpoints reject unauthenticated requests with 401."""
    assert client.get("/api/v1/customers").status_code == 401
    assert client.get("/api/v1/subscriptions").status_code == 401
    assert client.get("/api/v1/invoices").status_code == 401
    assert client.get("/api/v1/reports/dashboard").status_code == 401


def test_invalid_jwt_token_rejected(client):
    """Verify tampered or malformed Bearer tokens are rejected with 401."""
    bad_headers = {"Authorization": "Bearer invalid.tampered.token"}
    assert client.get("/api/v1/auth/me", headers=bad_headers).status_code == 401


def test_duplicate_email_registration_rejected(client):
    """Verify registering with an already-existing email address is rejected."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@acmecloud.io",
            "password": "ValidPassword#123",
            "full_name": "Duplicate Alice",
        },
    )
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


def test_staff_cannot_create_staff_or_admin_account(client):
    """Verify only System Administrators can provision staff/admin accounts."""
    staff_headers = get_auth_headers(client, "staff@submanage.io", "Staff@12345")
    resp = client.post(
        "/api/v1/auth/staff",
        headers=staff_headers,
        json={
            "email": "unauthorized.staff@submanage.io",
            "password": "StaffPassword#123",
            "full_name": "Unauthorized Staff",
            "role": "staff",
        },
    )
    assert resp.status_code == 403


def test_customer_cannot_perform_staff_or_admin_operations(client):
    """Verify Customer role cannot access Finance Dashboard, create products/plans, or provision staff."""
    alice_headers = get_auth_headers(client, "alice@acmecloud.io", "Customer@123")

    # Cannot view staff finance dashboard
    assert client.get("/api/v1/reports/dashboard", headers=alice_headers).status_code == 403

    # Cannot create products
    assert (
        client.post(
            "/api/v1/products",
            headers=alice_headers,
            json={"name": "Hack Product", "sales_price": "10.00"},
        ).status_code
        == 403
    )

    # Cannot create plans
    assert (
        client.post(
            "/api/v1/plans",
            headers=alice_headers,
            json={"name": "Hack Plan", "billing_interval": "monthly"},
        ).status_code
        == 403
    )

    # Cannot create staff
    assert (
        client.post(
            "/api/v1/auth/staff",
            headers=alice_headers,
            json={
                "email": "hack@submanage.io",
                "password": "HackPassword#123",
                "full_name": "Hack",
                "role": "admin",
            },
        ).status_code
        == 403
    )


def test_strict_customer_data_isolation_against_idor(client):
    """Verify Customer A (Alice) cannot read or pay Customer C's (Carol) subscriptions, invoices, or profile by ID."""
    staff_headers = get_auth_headers(client, "staff@submanage.io", "Staff@12345")
    alice_headers = get_auth_headers(client, "alice@acmecloud.io", "Customer@123")

    alice_me = client.get("/api/v1/auth/me", headers=alice_headers).json()
    alice_customer_id = alice_me["customer_id"]
    assert "password_hash" not in alice_me

    # Find another customer's subscription and invoice via staff
    all_subs = client.get("/api/v1/subscriptions", headers=staff_headers).json()
    other_sub = next(s for s in all_subs if s["customer_id"] != alice_customer_id)

    all_invs = client.get("/api/v1/invoices", headers=staff_headers).json()
    other_inv = next(i for i in all_invs if i["customer_id"] != alice_customer_id)

    # Alice trying to read another customer's profile by ID -> 403 Forbidden
    assert (
        client.get(
            f"/api/v1/customers/{other_sub['customer_id']}", headers=alice_headers
        ).status_code
        == 403
    )

    # Alice trying to read another customer's subscription by ID -> 403 Forbidden
    assert (
        client.get(
            f"/api/v1/subscriptions/{other_sub['id']}", headers=alice_headers
        ).status_code
        == 403
    )

    # Alice trying to read another customer's invoice or balance by ID -> 403 Forbidden
    assert (
        client.get(f"/api/v1/invoices/{other_inv['id']}", headers=alice_headers).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/invoices/{other_inv['id']}/balance", headers=alice_headers
        ).status_code
        == 403
    )

    # List endpoints scoped strictly to Alice's customer_id
    alice_subs = client.get("/api/v1/subscriptions", headers=alice_headers).json()
    assert all(s["customer_id"] == alice_customer_id for s in alice_subs)

    alice_invs = client.get("/api/v1/invoices", headers=alice_headers).json()
    assert all(i["customer_id"] == alice_customer_id for i in alice_invs)

