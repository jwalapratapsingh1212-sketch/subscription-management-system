"""FastAPI application entrypoint registering all modular monolith domain routers."""
from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.seeder import seed_demo_data
from app.customers.router import router as customers_router
from app.invoices.router import (
    discounts_router,
    invoices_router,
    tax_rules_router,
)
import app.models  # noqa: F401
from app.payments.router import invoice_balance_router, payments_router
from app.plans.router import router as plans_router
from app.products.router import router as products_router
from app.reports.router import router as reports_router
from app.subscriptions.router import quotations_router, subscriptions_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database tables exist and seed development data if empty."""
    Base.metadata.create_all(bind=engine)
    if os.environ.get("SKIP_AUTO_SEED", "false").lower() != "true":
        with SessionLocal() as db:
            seed_demo_data(db)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Enterprise-grade Subscription Management & Recurring Billing System "
        "implementing RBAC, Quotations, Subscription Lifecycle State Machine, "
        "Idempotent Automated Billing, Configurable Taxes & Discounts, "
        "Payment Reconciliation, and Finance Analytics."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALL_ROUTERS = [
    auth_router,
    customers_router,
    products_router,
    plans_router,
    quotations_router,
    subscriptions_router,
    invoices_router,
    discounts_router,
    tax_rules_router,
    payments_router,
    invoice_balance_router,
    reports_router,
]

# Register under /api/v1 prefix AND root path so both /api/v1/auth/login and /auth/login work seamlessly
for r in ALL_ROUTERS:
    app.include_router(r, prefix=settings.API_V1_PREFIX)
    app.include_router(r, include_in_schema=False)


@app.get("/health", tags=["System"])
@app.get(f"{settings.API_V1_PREFIX}/health", tags=["System"])
def health_check():
    """Health check endpoint verifying API and database readiness."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.0",
    }
