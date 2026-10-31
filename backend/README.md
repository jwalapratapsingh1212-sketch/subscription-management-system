# Backend

The backend is a FastAPI application that exposes the subscription and billing domain through REST endpoints. It uses SQLAlchemy for persistence, Pydantic for request/response validation, and PostgreSQL as the primary database.

## Responsibilities

- Authentication, JWT sessions, and role-based access.
- Customer, product, plan, quotation, and subscription operations.
- Invoice generation, payment recording, discounts, and tax rules.
- Finance and operational reporting.
- Database access, audit logging, configuration, and demo-data seeding.

## Project layout

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI app, lifespan, middleware, and router registration |
| `app/auth/` | Authentication endpoints, schemas, and services |
| `app/core/` | Configuration, database, security, permissions, and shared utilities |
| `app/customers/` | Customer domain |
| `app/products/` | Product catalogue |
| `app/plans/` | Subscription plans |
| `app/subscriptions/` | Quotations and subscription lifecycle |
| `app/invoices/` | Invoices, discounts, and tax rules |
| `app/payments/` | Payments and invoice balances |
| `app/reports/` | Dashboard and reporting endpoints |

## Local setup

Run commands from the repository root.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On macOS/Linux, activate with `source .venv/bin/activate`.

Create a local `.env` using the root `.env.example` as a reference. Review all values before starting the service. The settings module supports a PostgreSQL URL and a local SQLite fallback when enabled.

```powershell
uvicorn app.main:app --reload
```

API documentation is normally available at `http://127.0.0.1:8000/docs`; health endpoints are `/health` and `/api/v1/health`.

## Configuration notes

Important settings include `DATABASE_URL`, `FALLBACK_SQLITE_URL`, `AUTO_FALLBACK_TO_SQLITE`, `JWT_SECRET_KEY`, `APP_ENV`, `APP_DEBUG`, `API_V1_PREFIX`, and `CORS_ORIGINS`. Use a unique secret and explicit trusted origins outside local demos.

The application currently creates missing tables during startup and seeds demo records unless `SKIP_AUTO_SEED=true`. For controlled environments, use migrations and manage seed behavior deliberately.

## Tests

From the repository root:

```powershell
python -m pytest tests -q
```

See [tests/README.md](../tests/README.md) for test fixtures and coverage notes.

## Security and production warning

The repository contains demo credentials and development-oriented defaults for judging and local evaluation. They are not production credentials. Before deployment, replace all secrets, restrict CORS, disable automatic demo seeding, configure email-based password reset delivery, use HTTPS, and review tenant authorization. The current password-reset flow returns a reset token in the API response, which is suitable only for a controlled demo and must be redesigned for production.

**Verification status:** These instructions describe the checked-in source configuration. They do not certify that the application has been successfully started or that all tests pass on every machine.
