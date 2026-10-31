-- ============================================================================
-- PostgreSQL Normalized Schema Migration (001_initial_schema.sql)
-- Subscription Management System
-- Uses NUMERIC(12, 2) for all monetary fields, strict Foreign Keys,
-- Check Constraints, Unique Constraints, and Performance Indexes.
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL DEFAULT '',
    password_hash VARCHAR(512) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'customer' CHECK (role IN ('admin', 'staff', 'customer')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    reset_token VARCHAR(512),
    reset_token_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(64),
    tax_id VARCHAR(64),
    billing_address TEXT NOT NULL DEFAULT '',
    city VARCHAR(128),
    state VARCHAR(128),
    country VARCHAR(128) DEFAULT 'US',
    postal_code VARCHAR(32),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_customers_user_id ON customers (user_id);
CREATE INDEX IF NOT EXISTS ix_customers_email ON customers (email);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    product_type VARCHAR(64) NOT NULL DEFAULT 'service',
    sales_price NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (sales_price >= 0),
    cost_price NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (cost_price >= 0),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_products_is_active ON products (is_active);

CREATE TABLE IF NOT EXISTS product_variants (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(64),
    attribute_name VARCHAR(128),
    attribute_value VARCHAR(128),
    price_extra NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (price_extra >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_product_variants_product_id ON product_variants (product_id);

CREATE TABLE IF NOT EXISTS plans (
    id SERIAL PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    billing_interval VARCHAR(32) NOT NULL DEFAULT 'monthly'
        CHECK (billing_interval IN ('daily', 'weekly', 'monthly', 'yearly')),
    minimum_quantity INTEGER NOT NULL DEFAULT 1 CHECK (minimum_quantity >= 1),
    available_from DATE,
    available_until DATE,
    trial_period_days INTEGER NOT NULL DEFAULT 0,
    default_payment_term_days INTEGER NOT NULL DEFAULT 14,
    auto_close BOOLEAN NOT NULL DEFAULT FALSE,
    early_close_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    pause_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    resume_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    renewal_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tax_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(64) NOT NULL UNIQUE,
    rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00 CHECK (rate >= 0 AND rate <= 100),
    region VARCHAR(128) NOT NULL DEFAULT 'Global',
    category VARCHAR(128) NOT NULL DEFAULT 'Standard',
    effective_from DATE,
    effective_until DATE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS discounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(64) NOT NULL UNIQUE,
    discount_type VARCHAR(32) NOT NULL DEFAULT 'percentage'
        CHECK (discount_type IN ('fixed', 'percentage')),
    value NUMERIC(12, 2) NOT NULL CHECK (value > 0),
    min_purchase_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (min_purchase_amount >= 0),
    min_quantity INTEGER NOT NULL DEFAULT 0 CHECK (min_quantity >= 0),
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    applicable_to VARCHAR(32) NOT NULL DEFAULT 'all',
    start_date DATE,
    end_date DATE,
    usage_limit INTEGER,
    usage_count INTEGER NOT NULL DEFAULT 0 CHECK (usage_count >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quotation_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    validity_days INTEGER NOT NULL DEFAULT 30,
    payment_terms VARCHAR(128) NOT NULL DEFAULT 'Net 14',
    notes TEXT,
    default_lines_json TEXT NOT NULL DEFAULT '[]',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quotations (
    id SERIAL PRIMARY KEY,
    quotation_number VARCHAR(64) NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    template_id INTEGER REFERENCES quotation_templates(id) ON DELETE SET NULL,
    discount_id INTEGER REFERENCES discounts(id) ON DELETE SET NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'sent', 'confirmed', 'expired', 'cancelled')),
    valid_until DATE NOT NULL,
    start_date DATE,
    payment_terms VARCHAR(128) NOT NULL DEFAULT 'Net 14',
    notes TEXT,
    subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    total NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (total >= 0),
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_quotations_customer_id ON quotations (customer_id);
CREATE INDEX IF NOT EXISTS ix_quotations_status ON quotations (status);

CREATE TABLE IF NOT EXISTS quotation_lines (
    id SERIAL PRIMARY KEY,
    quotation_id INTEGER NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    variant_id INTEGER REFERENCES product_variants(id) ON DELETE SET NULL,
    tax_rule_id INTEGER REFERENCES tax_rules(id) ON DELETE SET NULL,
    description VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    line_subtotal NUMERIC(12, 2) NOT NULL,
    line_tax NUMERIC(12, 2) NOT NULL,
    line_total NUMERIC(12, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_number VARCHAR(64) NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    quotation_id INTEGER REFERENCES quotations(id) ON DELETE SET NULL,
    discount_id INTEGER REFERENCES discounts(id) ON DELETE SET NULL,
    state VARCHAR(32) NOT NULL DEFAULT 'draft'
        CHECK (state IN ('draft', 'quotation', 'confirmed', 'active', 'paused', 'past_due', 'closed')),
    start_date DATE NOT NULL,
    expiry_date DATE,
    next_billing_date DATE,
    paused_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    payment_terms VARCHAR(128) NOT NULL DEFAULT 'Net 14',
    payment_term_days INTEGER NOT NULL DEFAULT 14,
    auto_renew BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    recurring_subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    recurring_discount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    recurring_tax NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    recurring_total NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_subscriptions_customer_id ON subscriptions (customer_id);
CREATE INDEX IF NOT EXISTS ix_subscriptions_state ON subscriptions (state);
CREATE INDEX IF NOT EXISTS ix_subscriptions_next_billing_date ON subscriptions (next_billing_date);
CREATE INDEX IF NOT EXISTS ix_subscriptions_state_next_billing ON subscriptions (state, next_billing_date);

CREATE TABLE IF NOT EXISTS subscription_lines (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    variant_id INTEGER REFERENCES product_variants(id) ON DELETE SET NULL,
    tax_rule_id INTEGER REFERENCES tax_rules(id) ON DELETE SET NULL,
    description VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    line_subtotal NUMERIC(12, 2) NOT NULL,
    line_tax NUMERIC(12, 2) NOT NULL,
    line_total NUMERIC(12, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(64) NOT NULL UNIQUE,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(id),
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    discount_id INTEGER REFERENCES discounts(id) ON DELETE SET NULL,
    billing_period_start DATE NOT NULL,
    billing_period_end DATE NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    state VARCHAR(32) NOT NULL DEFAULT 'draft'
        CHECK (state IN ('draft', 'confirmed', 'paid', 'cancelled')),
    payment_status VARCHAR(32) NOT NULL DEFAULT 'unpaid'
        CHECK (payment_status IN ('unpaid', 'partially_paid', 'paid', 'overdue', 'cancelled')),
    subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    total NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (total >= 0),
    amount_paid NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (amount_paid >= 0),
    amount_due NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (amount_due >= 0),
    notes TEXT,
    confirmed_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_invoice_subscription_billing_period
        UNIQUE (subscription_id, billing_period_start, billing_period_end)
);

CREATE INDEX IF NOT EXISTS ix_invoices_subscription_id ON invoices (subscription_id);
CREATE INDEX IF NOT EXISTS ix_invoices_customer_id ON invoices (customer_id);
CREATE INDEX IF NOT EXISTS ix_invoices_due_date_state ON invoices (due_date, state);

CREATE TABLE IF NOT EXISTS invoice_lines (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    variant_id INTEGER REFERENCES product_variants(id) ON DELETE SET NULL,
    tax_rule_id INTEGER REFERENCES tax_rules(id) ON DELETE SET NULL,
    description VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    line_subtotal NUMERIC(12, 2) NOT NULL,
    line_tax NUMERIC(12, 2) NOT NULL,
    line_total NUMERIC(12, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    payment_number VARCHAR(64) NOT NULL UNIQUE,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id),
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    method VARCHAR(64) NOT NULL DEFAULT 'credit_card',
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    payment_date DATE NOT NULL,
    reference VARCHAR(128),
    note TEXT,
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'succeeded'
        CHECK (status IN ('succeeded', 'failed', 'refunded')),
    recorded_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_payments_invoice_id ON payments (invoice_id);
CREATE INDEX IF NOT EXISTS ix_payments_customer_id ON payments (customer_id);
CREATE INDEX IF NOT EXISTS ix_payments_idempotency_key ON payments (idempotency_key);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    actor_email VARCHAR(255),
    actor_role VARCHAR(32),
    action VARCHAR(128) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs (timestamp);

CREATE TABLE IF NOT EXISTS billing_jobs (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    billing_period_start DATE NOT NULL,
    billing_period_end DATE NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(32) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    locked_at TIMESTAMPTZ,
    worker_id VARCHAR(64),
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    invoice_id INTEGER REFERENCES invoices(id) ON DELETE SET NULL,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT uq_billing_job_sub_period
        UNIQUE (subscription_id, billing_period_start, billing_period_end)
);

CREATE INDEX IF NOT EXISTS ix_billing_jobs_status_scheduled ON billing_jobs (status, scheduled_at);

