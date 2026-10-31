"""Idempotent development & demonstration data seeder."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    AuditLog,
    Customer,
    Discount,
    Invoice,
    InvoiceLine,
    Payment,
    Plan,
    Product,
    ProductVariant,
    Quotation,
    QuotationLine,
    QuotationTemplate,
    Subscription,
    SubscriptionLine,
    TaxRule,
    User,
)


def seed_demo_data(db: Session) -> dict:
    """Populate realistic development data if the database is empty."""
    if db.query(User).count() > 0:
        return {"seeded": False, "message": "Database already contains records."}

    today = date.today()
    now_utc = datetime.now(timezone.utc)

    # 1. Users (Admin, Staff, Customers)
    admin_user = User(
        email="admin@submanage.io",
        full_name="Elena Rostova (System Admin)",
        password_hash=hash_password("Admin@12345"),
        role="admin",
        is_active=True,
    )
    staff_user = User(
        email="staff@submanage.io",
        full_name="Marcus Vance (Billing Operations)",
        password_hash=hash_password("Staff@12345"),
        role="staff",
        is_active=True,
    )
    cust_user_1 = User(
        email="alice@acmecloud.io",
        full_name="Alice Chen",
        password_hash=hash_password("Customer@123"),
        role="customer",
        is_active=True,
    )
    cust_user_2 = User(
        email="bob@globalfintech.io",
        full_name="Robert Sterling",
        password_hash=hash_password("Customer@123"),
        role="customer",
        is_active=True,
    )
    cust_user_3 = User(
        email="carol@nexushealth.io",
        full_name="Dr. Carol Martinez",
        password_hash=hash_password("Customer@123"),
        role="customer",
        is_active=True,
    )
    db.add_all([admin_user, staff_user, cust_user_1, cust_user_2, cust_user_3])
    db.flush()

    # 2. Customers
    cust_1 = Customer(
        user_id=cust_user_1.id,
        name="Alice Chen",
        company_name="Acme Cloud Technologies Inc.",
        email="alice@acmecloud.io",
        phone="+1 (415) 890-2310",
        tax_id="US-94-3829104",
        billing_address="742 Evergreen Innovation Way, Suite 400",
        city="San Francisco",
        state="CA",
        country="US",
        postal_code="94107",
        notes="Enterprise cloud infrastructure customer.",
        is_active=True,
    )
    cust_2 = Customer(
        user_id=cust_user_2.id,
        name="Robert Sterling",
        company_name="Global FinTech Holdings Ltd.",
        email="bob@globalfintech.io",
        phone="+1 (212) 555-0194",
        tax_id="US-13-8492011",
        billing_address="One World Financial Plaza, Floor 32",
        city="New York",
        state="NY",
        country="US",
        postal_code="10281",
        notes="High-volume annual financial platform subscriber.",
        is_active=True,
    )
    cust_3 = Customer(
        user_id=cust_user_3.id,
        name="Dr. Carol Martinez",
        company_name="Nexus Health AI Diagnostics",
        email="carol@nexushealth.io",
        phone="+1 (617) 555-0148",
        tax_id="US-04-7721903",
        billing_address="200 Kendall Square Biotech Hub",
        city="Cambridge",
        state="MA",
        country="US",
        postal_code="02139",
        notes="Healthcare AI analytics subscriber.",
        is_active=True,
    )
    db.add_all([cust_1, cust_2, cust_3])
    db.flush()

    # 3. Tax Rules
    tax_us = TaxRule(
        name="US Standard SaaS Sales Tax",
        code="TAX-US-STD",
        rate=Decimal("10.00"),
        region="United States",
        category="Digital & SaaS",
        is_default=True,
        is_active=True,
    )
    tax_eu = TaxRule(
        name="EU Digital Services VAT",
        code="TAX-EU-VAT",
        rate=Decimal("20.00"),
        region="European Union",
        category="Digital Services",
        is_default=False,
        is_active=True,
    )
    tax_zero = TaxRule(
        name="Tax Exempt / Export",
        code="TAX-EXEMPT",
        rate=Decimal("0.00"),
        region="Global",
        category="Exempt",
        is_default=False,
        is_active=True,
    )
    db.add_all([tax_us, tax_eu, tax_zero])
    db.flush()

    # 4. Products & Variants
    prod_platform = Product(
        sku="PRD-SAAS-CORE",
        name="Enterprise Cloud Core Platform",
        product_type="software",
        sales_price=Decimal("300.00"),
        cost_price=Decimal("45.00"),
        notes="Core multi-region SaaS orchestration platform license.",
        is_active=True,
    )
    prod_copilot = Product(
        sku="PRD-AI-COPILOT",
        name="AI Revenue & Billing Copilot Seat",
        product_type="service",
        sales_price=Decimal("50.00"),
        cost_price=Decimal("12.00"),
        notes="Per-operator intelligent forecasting and anomaly detection seat.",
        is_active=True,
    )
    prod_security = Product(
        sku="PRD-SEC-COMPLIANCE",
        name="SOC2 & ISO27001 Compliance Guard",
        product_type="software",
        sales_price=Decimal("200.00"),
        cost_price=Decimal("30.00"),
        notes="Automated security posture and audit trail module.",
        is_active=True,
    )
    db.add_all([prod_platform, prod_copilot, prod_security])
    db.flush()

    var_pro_support = ProductVariant(
        product_id=prod_platform.id,
        name="24/7 Mission-Critical SLA",
        sku="VAR-SLA-247",
        attribute_name="Support Level",
        attribute_value="24/7 Dedicated",
        price_extra=Decimal("100.00"),
        is_active=True,
    )
    var_dedicated = ProductVariant(
        product_id=prod_platform.id,
        name="Dedicated VPC Cluster",
        sku="VAR-VPC-DED",
        attribute_name="Deployment",
        attribute_value="Isolated VPC",
        price_extra=Decimal("250.00"),
        is_active=True,
    )
    var_unlimited_ai = ProductVariant(
        product_id=prod_copilot.id,
        name="Unlimited Token Pack",
        sku="VAR-AI-UNLIM",
        attribute_name="Capacity",
        attribute_value="Unlimited",
        price_extra=Decimal("25.00"),
        is_active=True,
    )
    db.add_all([var_pro_support, var_dedicated, var_unlimited_ai])
    db.flush()

    # 5. Plans
    plan_monthly = Plan(
        code="PLN-MONTHLY",
        name="Monthly Growth Plan",
        description="Flexible month-to-month billing with full pause, resume, and renewal options.",
        billing_interval="monthly",
        minimum_quantity=1,
        trial_period_days=0,
        default_payment_term_days=14,
        auto_close=False,
        early_close_allowed=True,
        pause_allowed=True,
        resume_allowed=True,
        renewal_allowed=True,
        is_active=True,
    )
    plan_yearly = Plan(
        code="PLN-YEARLY",
        name="Annual Enterprise Commitment",
        description="Annual billing cycle for enterprise teams (minimum 2 units, locked term).",
        billing_interval="yearly",
        minimum_quantity=2,
        trial_period_days=14,
        default_payment_term_days=30,
        auto_close=False,
        early_close_allowed=False,
        pause_allowed=True,
        resume_allowed=True,
        renewal_allowed=True,
        is_active=True,
    )
    plan_weekly = Plan(
        code="PLN-WEEKLY",
        name="Weekly Sprint Compute Plan",
        description="Short-term weekly recurring billing with automatic closure at term end.",
        billing_interval="weekly",
        minimum_quantity=1,
        default_payment_term_days=7,
        auto_close=True,
        early_close_allowed=True,
        pause_allowed=False,
        resume_allowed=False,
        renewal_allowed=True,
        is_active=True,
    )
    plan_daily = Plan(
        code="PLN-DAILY",
        name="Daily Burst Sandbox Plan",
        description="Daily recurring billing for elastic testing environments.",
        billing_interval="daily",
        minimum_quantity=1,
        default_payment_term_days=1,
        auto_close=True,
        early_close_allowed=True,
        pause_allowed=False,
        resume_allowed=False,
        renewal_allowed=False,
        is_active=True,
    )
    db.add_all([plan_monthly, plan_yearly, plan_weekly, plan_daily])
    db.flush()

    # 6. Discounts
    disc_welcome = Discount(
        name="Welcome 10% SaaS Promo",
        code="WELCOME10",
        discount_type="percentage",
        value=Decimal("10.00"),
        min_purchase_amount=Decimal("100.00"),
        min_quantity=1,
        applicable_to="all",
        start_date=today - timedelta(days=90),
        end_date=today + timedelta(days=180),
        usage_limit=100,
        usage_count=2,
        is_active=True,
    )
    disc_fixed = Discount(
        name="Enterprise $100 Rebate",
        code="ENT100",
        discount_type="fixed",
        value=Decimal("100.00"),
        min_purchase_amount=Decimal("500.00"),
        min_quantity=2,
        applicable_to="subscription",
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=120),
        usage_limit=50,
        usage_count=1,
        is_active=True,
    )
    db.add_all([disc_welcome, disc_fixed])
    db.flush()

    # 7. Quotation Templates
    tpl_saas = QuotationTemplate(
        name="Standard SaaS Growth Bundle",
        description="Pre-configured monthly quote with Core Platform + 5 AI Copilot seats.",
        plan_id=plan_monthly.id,
        validity_days=30,
        payment_terms="Net 14",
        notes="Includes standard onboarding and 99.9% uptime SLA.",
        default_lines_json=json.dumps(
            [
                {"product_id": prod_platform.id, "quantity": 1, "tax_rate": "10.00"},
                {"product_id": prod_copilot.id, "quantity": 5, "tax_rate": "10.00"},
            ]
        ),
        is_active=True,
    )
    db.add(tpl_saas)
    db.flush()

    # 8. Quotations
    quote_confirmed = Quotation(
        quotation_number="QT-2026-0001",
        customer_id=cust_1.id,
        plan_id=plan_monthly.id,
        template_id=tpl_saas.id,
        discount_id=disc_welcome.id,
        status="confirmed",
        valid_until=today + timedelta(days=30),
        start_date=today - timedelta(days=30),
        payment_terms="Net 14",
        notes="Approved by Acme Cloud Procurement.",
        subtotal=Decimal("650.00"),
        discount_amount=Decimal("65.00"),
        tax_amount=Decimal("58.50"),
        total=Decimal("643.50"),
        created_by_id=staff_user.id,
    )
    quote_sent = Quotation(
        quotation_number="QT-2026-0002",
        customer_id=cust_3.id,
        plan_id=plan_monthly.id,
        status="sent",
        valid_until=today + timedelta(days=21),
        start_date=today + timedelta(days=3),
        payment_terms="Net 14",
        notes="Pending Nexus Health board review — ready for one-click confirmation.",
        subtotal=Decimal("500.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("50.00"),
        total=Decimal("550.00"),
        created_by_id=staff_user.id,
    )
    db.add_all([quote_confirmed, quote_sent])
    db.flush()

    db.add_all(
        [
            QuotationLine(
                quotation_id=quote_confirmed.id,
                product_id=prod_platform.id,
                variant_id=var_pro_support.id,
                tax_rule_id=tax_us.id,
                description="Enterprise Cloud Core Platform (24/7 Mission-Critical SLA)",
                quantity=1,
                unit_price=Decimal("400.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("400.00"),
                line_tax=Decimal("36.00"),
                line_total=Decimal("436.00"),
            ),
            QuotationLine(
                quotation_id=quote_confirmed.id,
                product_id=prod_copilot.id,
                tax_rule_id=tax_us.id,
                description="AI Revenue & Billing Copilot Seat",
                quantity=5,
                unit_price=Decimal("50.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("250.00"),
                line_tax=Decimal("22.50"),
                line_total=Decimal("272.50"),
            ),
            QuotationLine(
                quotation_id=quote_sent.id,
                product_id=prod_platform.id,
                tax_rule_id=tax_us.id,
                description="Enterprise Cloud Core Platform",
                quantity=1,
                unit_price=Decimal("300.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("300.00"),
                line_tax=Decimal("30.00"),
                line_total=Decimal("330.00"),
            ),
            QuotationLine(
                quotation_id=quote_sent.id,
                product_id=prod_security.id,
                tax_rule_id=tax_us.id,
                description="SOC2 & ISO27001 Compliance Guard",
                quantity=1,
                unit_price=Decimal("200.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("200.00"),
                line_tax=Decimal("20.00"),
                line_total=Decimal("220.00"),
            ),
        ]
    )

    # 9. Subscriptions
    sub_1 = Subscription(
        subscription_number="SUB-2026-0001",
        customer_id=cust_1.id,
        plan_id=plan_monthly.id,
        quotation_id=quote_confirmed.id,
        discount_id=disc_welcome.id,
        state="active",
        start_date=today - timedelta(days=30),
        expiry_date=today + timedelta(days=335),
        next_billing_date=today,  # Due today for live billing demo!
        payment_terms="Net 14",
        payment_term_days=14,
        auto_renew=True,
        notes="Primary production SaaS subscription for Acme Cloud.",
        recurring_subtotal=Decimal("650.00"),
        recurring_discount=Decimal("65.00"),
        recurring_tax=Decimal("58.50"),
        recurring_total=Decimal("643.50"),
    )
    sub_2 = Subscription(
        subscription_number="SUB-2026-0002",
        customer_id=cust_2.id,
        plan_id=plan_yearly.id,
        discount_id=disc_fixed.id,
        state="active",
        start_date=today - timedelta(days=45),
        expiry_date=today + timedelta(days=320),
        next_billing_date=today + timedelta(days=320),
        payment_terms="Net 30",
        payment_term_days=30,
        auto_renew=True,
        notes="Annual enterprise cluster subscription for Global FinTech.",
        recurring_subtotal=Decimal("1500.00"),
        recurring_discount=Decimal("100.00"),
        recurring_tax=Decimal("140.00"),
        recurring_total=Decimal("1540.00"),
    )
    sub_3 = Subscription(
        subscription_number="SUB-2026-0003",
        customer_id=cust_3.id,
        plan_id=plan_monthly.id,
        state="past_due",
        start_date=today - timedelta(days=40),
        expiry_date=today + timedelta(days=325),
        next_billing_date=today + timedelta(days=20),
        payment_terms="Net 14",
        payment_term_days=14,
        auto_renew=True,
        notes="Has an overdue partially paid invoice awaiting balance settlement.",
        recurring_subtotal=Decimal("500.00"),
        recurring_discount=Decimal("0.00"),
        recurring_tax=Decimal("50.00"),
        recurring_total=Decimal("550.00"),
    )
    db.add_all([sub_1, sub_2, sub_3])
    db.flush()

    db.add_all(
        [
            SubscriptionLine(
                subscription_id=sub_1.id,
                product_id=prod_platform.id,
                variant_id=var_pro_support.id,
                tax_rule_id=tax_us.id,
                description="Enterprise Cloud Core Platform (24/7 Mission-Critical SLA)",
                quantity=1,
                unit_price=Decimal("400.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("400.00"),
                line_tax=Decimal("36.00"),
                line_total=Decimal("436.00"),
            ),
            SubscriptionLine(
                subscription_id=sub_1.id,
                product_id=prod_copilot.id,
                tax_rule_id=tax_us.id,
                description="AI Revenue & Billing Copilot Seat",
                quantity=5,
                unit_price=Decimal("50.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("250.00"),
                line_tax=Decimal("22.50"),
                line_total=Decimal("272.50"),
            ),
            SubscriptionLine(
                subscription_id=sub_2.id,
                product_id=prod_platform.id,
                variant_id=var_dedicated.id,
                tax_rule_id=tax_us.id,
                description="Enterprise Cloud Core Platform (Dedicated VPC Cluster)",
                quantity=2,
                unit_price=Decimal("550.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("1100.00"),
                line_tax=Decimal("102.67"),
                line_total=Decimal("1202.67"),
            ),
            SubscriptionLine(
                subscription_id=sub_2.id,
                product_id=prod_security.id,
                tax_rule_id=tax_us.id,
                description="SOC2 & ISO27001 Compliance Guard",
                quantity=2,
                unit_price=Decimal("200.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("400.00"),
                line_tax=Decimal("37.33"),
                line_total=Decimal("437.33"),
            ),
            SubscriptionLine(
                subscription_id=sub_3.id,
                product_id=prod_platform.id,
                tax_rule_id=tax_us.id,
                description="Enterprise Cloud Core Platform",
                quantity=1,
                unit_price=Decimal("300.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("300.00"),
                line_tax=Decimal("30.00"),
                line_total=Decimal("330.00"),
            ),
            SubscriptionLine(
                subscription_id=sub_3.id,
                product_id=prod_security.id,
                tax_rule_id=tax_us.id,
                description="SOC2 & ISO27001 Compliance Guard",
                quantity=1,
                unit_price=Decimal("200.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("200.00"),
                line_tax=Decimal("20.00"),
                line_total=Decimal("220.00"),
            ),
        ]
    )

    # 10. Invoices (1 Paid, 1 Paid Annual, 1 Overdue Partially Paid)
    inv_1 = Invoice(
        invoice_number="INV-2026-0001",
        subscription_id=sub_1.id,
        customer_id=cust_1.id,
        discount_id=disc_welcome.id,
        billing_period_start=today - timedelta(days=30),
        billing_period_end=today - timedelta(days=1),
        issue_date=today - timedelta(days=30),
        due_date=today - timedelta(days=16),
        state="paid",
        payment_status="paid",
        subtotal=Decimal("650.00"),
        discount_amount=Decimal("65.00"),
        tax_amount=Decimal("58.50"),
        total=Decimal("643.50"),
        amount_paid=Decimal("643.50"),
        amount_due=Decimal("0.00"),
        notes="Initial monthly cycle — paid in full.",
        confirmed_at=now_utc - timedelta(days=30),
        paid_at=now_utc - timedelta(days=25),
    )
    inv_2 = Invoice(
        invoice_number="INV-2026-0002",
        subscription_id=sub_2.id,
        customer_id=cust_2.id,
        discount_id=disc_fixed.id,
        billing_period_start=today - timedelta(days=45),
        billing_period_end=today + timedelta(days=319),
        issue_date=today - timedelta(days=45),
        due_date=today - timedelta(days=15),
        state="paid",
        payment_status="paid",
        subtotal=Decimal("1500.00"),
        discount_amount=Decimal("100.00"),
        tax_amount=Decimal("140.00"),
        total=Decimal("1540.00"),
        amount_paid=Decimal("1540.00"),
        amount_due=Decimal("0.00"),
        notes="Annual prepayment invoice — demonstrates deferred vs recognized revenue.",
        confirmed_at=now_utc - timedelta(days=45),
        paid_at=now_utc - timedelta(days=40),
    )
    inv_3 = Invoice(
        invoice_number="INV-2026-0003",
        subscription_id=sub_3.id,
        customer_id=cust_3.id,
        billing_period_start=today - timedelta(days=40),
        billing_period_end=today - timedelta(days=11),
        issue_date=today - timedelta(days=40),
        due_date=today - timedelta(days=12),
        state="confirmed",
        payment_status="overdue",
        subtotal=Decimal("500.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("50.00"),
        total=Decimal("550.00"),
        amount_paid=Decimal("200.00"),
        amount_due=Decimal("350.00"),
        notes="Partially paid invoice past due date — $350.00 remaining balance.",
        confirmed_at=now_utc - timedelta(days=40),
    )
    db.add_all([inv_1, inv_2, inv_3])
    db.flush()

    db.add_all(
        [
            InvoiceLine(
                invoice_id=inv_1.id,
                product_id=prod_platform.id,
                variant_id=var_pro_support.id,
                tax_rule_id=tax_us.id,
                description="Enterprise Cloud Core Platform (24/7 Mission-Critical SLA)",
                quantity=1,
                unit_price=Decimal("400.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("400.00"),
                line_tax=Decimal("36.00"),
                line_total=Decimal("436.00"),
            ),
            InvoiceLine(
                invoice_id=inv_1.id,
                product_id=prod_copilot.id,
                tax_rule_id=tax_us.id,
                description="AI Revenue & Billing Copilot Seat",
                quantity=5,
                unit_price=Decimal("50.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("250.00"),
                line_tax=Decimal("22.50"),
                line_total=Decimal("272.50"),
            ),
            InvoiceLine(
                invoice_id=inv_2.id,
                product_id=prod_platform.id,
                variant_id=var_dedicated.id,
                tax_rule_id=tax_us.id,
                description="Enterprise Cloud Core Platform (Dedicated VPC Cluster)",
                quantity=2,
                unit_price=Decimal("550.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("1100.00"),
                line_tax=Decimal("102.67"),
                line_total=Decimal("1202.67"),
            ),
            InvoiceLine(
                invoice_id=inv_2.id,
                product_id=prod_security.id,
                tax_rule_id=tax_us.id,
                description="SOC2 & ISO27001 Compliance Guard",
                quantity=2,
                unit_price=Decimal("200.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("400.00"),
                line_tax=Decimal("37.33"),
                line_total=Decimal("437.33"),
            ),
            InvoiceLine(
                invoice_id=inv_3.id,
                product_id=prod_platform.id,
                tax_rule_id=tax_us.id,
                description="Enterprise Cloud Core Platform",
                quantity=1,
                unit_price=Decimal("300.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("300.00"),
                line_tax=Decimal("30.00"),
                line_total=Decimal("330.00"),
            ),
            InvoiceLine(
                invoice_id=inv_3.id,
                product_id=prod_security.id,
                tax_rule_id=tax_us.id,
                description="SOC2 & ISO27001 Compliance Guard",
                quantity=1,
                unit_price=Decimal("200.00"),
                tax_rate=Decimal("10.00"),
                line_subtotal=Decimal("200.00"),
                line_tax=Decimal("20.00"),
                line_total=Decimal("220.00"),
            ),
        ]
    )

    # 11. Payments
    pay_1 = Payment(
        payment_number="PAY-2026-0001",
        invoice_id=inv_1.id,
        customer_id=cust_1.id,
        method="credit_card",
        amount=Decimal("643.50"),
        payment_date=today - timedelta(days=25),
        reference="STRIPE-CH-99201",
        note="Automatic corporate card settlement.",
        idempotency_key="seed-idem-key-0001",
        status="succeeded",
        recorded_by_id=staff_user.id,
    )
    pay_2 = Payment(
        payment_number="PAY-2026-0002",
        invoice_id=inv_2.id,
        customer_id=cust_2.id,
        method="wire",
        amount=Decimal("1540.00"),
        payment_date=today - timedelta(days=40),
        reference="FEDWIRE-883920",
        note="Annual enterprise wire transfer.",
        idempotency_key="seed-idem-key-0002",
        status="succeeded",
        recorded_by_id=admin_user.id,
    )
    pay_3 = Payment(
        payment_number="PAY-2026-0003",
        invoice_id=inv_3.id,
        customer_id=cust_3.id,
        method="bank_transfer",
        amount=Decimal("200.00"),
        payment_date=today - timedelta(days=20),
        reference="ACH-441092",
        note="Initial partial payment installment ($350.00 remaining).",
        idempotency_key="seed-idem-key-0003",
        status="succeeded",
        recorded_by_id=staff_user.id,
    )
    db.add_all([pay_1, pay_2, pay_3])

    db.add(
        AuditLog(
            actor_user_id=admin_user.id,
            actor_email=admin_user.email,
            actor_role=admin_user.role,
            action="system.seed_demo_data",
            entity_type="system",
            entity_id="init",
            metadata_json=json.dumps({"customers": 3, "products": 3, "plans": 4, "subscriptions": 3}),
        )
    )
    db.commit()
    return {"seeded": True, "message": "Demo data seeded successfully."}

