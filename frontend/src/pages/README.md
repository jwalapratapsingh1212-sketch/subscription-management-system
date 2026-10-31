# Route Pages

Pages are grouped by business domain. Route registration and access rules are centralized in [App.jsx](../App.jsx).

## Page groups

| Directory | Screen | Main purpose |
|---|---|---|
| `auth/` | `AuthPage` | Sign in, customer registration, and password reset |
| `dashboard/` | `DashboardPage` | Finance and operational overview |
| `customers/` | `CustomersPage` | Customer records |
| `products/` | `ProductsPage` | Products and variants |
| `plans/` | `PlansPage` | Subscription plan catalogue |
| `quotations/` | `QuotationsPage` | Quotation preparation and confirmation |
| `subscriptions/` | `SubscriptionsPage` | Subscription lifecycle operations |
| `invoices/` | `InvoicesPage` | Billing documents and invoice status |
| `discounts/` | `DiscountsPage` | Discount and tax-rule administration |
| `payments/` | `PaymentsPage` | Payment records and reconciliation views |
| `portal/` | `CustomerPortalPage` | Customer's quotations, subscriptions, invoices, and payments |

## Page responsibilities

A page coordinates the user interaction for one business area: loading data, managing local form/dialog state, calling the appropriate API service, and presenting success/error/loading feedback. Reusable visual primitives belong in [components](../components/README.md).

## Access control

The current route guard marks operational pages as staff-only and protects the portal behind authentication. The backend must independently authorize every API request and enforce customer/tenant data isolation.
