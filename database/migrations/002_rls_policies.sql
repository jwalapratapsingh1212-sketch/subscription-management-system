-- ============================================================================
-- PostgreSQL Row-Level Security (RLS) & Customer/Tenant Isolation Policies
-- Reference: Subscription_Management_System_Final_Architecture_Guide.pdf (pp. 8, 12)
--
-- Usage in PostgreSQL sessions:
--   SET LOCAL app.current_user_role = 'customer';
--   SET LOCAL app.current_customer_id = '42';
-- ============================================================================

ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE quotations ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- Policy 1: Admin and Staff have full access; Customer can only see their own row
DROP POLICY IF EXISTS customer_isolation_policy ON customers;
CREATE POLICY customer_isolation_policy ON customers
    USING (
        current_setting('app.current_user_role', true) IN ('admin', 'staff')
        OR id = NULLIF(current_setting('app.current_customer_id', true), '')::INTEGER
        OR current_setting('app.current_user_role', true) IS NULL
    );

DROP POLICY IF EXISTS quotation_customer_isolation ON quotations;
CREATE POLICY quotation_customer_isolation ON quotations
    USING (
        current_setting('app.current_user_role', true) IN ('admin', 'staff')
        OR customer_id = NULLIF(current_setting('app.current_customer_id', true), '')::INTEGER
        OR current_setting('app.current_user_role', true) IS NULL
    );

DROP POLICY IF EXISTS subscription_customer_isolation ON subscriptions;
CREATE POLICY subscription_customer_isolation ON subscriptions
    USING (
        current_setting('app.current_user_role', true) IN ('admin', 'staff')
        OR customer_id = NULLIF(current_setting('app.current_customer_id', true), '')::INTEGER
        OR current_setting('app.current_user_role', true) IS NULL
    );

DROP POLICY IF EXISTS invoice_customer_isolation ON invoices;
CREATE POLICY invoice_customer_isolation ON invoices
    USING (
        current_setting('app.current_user_role', true) IN ('admin', 'staff')
        OR customer_id = NULLIF(current_setting('app.current_customer_id', true), '')::INTEGER
        OR current_setting('app.current_user_role', true) IS NULL
    );

DROP POLICY IF EXISTS payment_customer_isolation ON payments;
CREATE POLICY payment_customer_isolation ON payments
    USING (
        current_setting('app.current_user_role', true) IN ('admin', 'staff')
        OR customer_id = NULLIF(current_setting('app.current_customer_id', true), '')::INTEGER
        OR current_setting('app.current_user_role', true) IS NULL
    );

