# REST API Reference

Base URL: `/api/v1`  
Interactive Swagger UI: `/docs`  
OpenAPI JSON Schema: `/openapi.json`

## 1. Authentication & Authorization Conventions

- **Authentication Scheme**: `Authorization: Bearer <jwt_access_token>` (RFC 7519 HS256).
- **Roles**:
  - `admin`: Full system access, including staff account provisioning, product/plan/tax deletion, and audit log inspection.
  - `internal_staff`: Operational ERP access to manage customers, products, plans, quotations, subscriptions, invoices, discounts, payments, and dashboard analytics.
  - `customer`: Self-service portal access strictly scoped to their own linked `Customer` profile, quotations, subscriptions, invoices, and payments.
- **Standard Error Payload**:
  ```json
  {
    "detail": "Human-readable explanation of the validation, authorization, or domain error"
  }
  ```

---

## 2. Endpoint Catalogue

### 2.1 System & Health
| Method | Path | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Public | Health check returning service status and version. |

### 2.2 Authentication & Identity (`/api/v1/auth`)
| Method | Path | Roles | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Public | Register a new customer user account and automatically create/link a `Customer` record. |
| `POST` | `/api/v1/auth/login` | Public | Authenticate with `email` and `password`; returns `access_token` and `user` profile. |
| `POST` | `/api/v1/auth/logout` | Any Authenticated | Log out the active session and record an audit event. |
| `GET` | `/api/v1/auth/me` | Any Authenticated | Retrieve the currently authenticated user profile. |
| `POST` | `/api/v1/auth/password-reset/request` | Public | Request a time-limited password reset token for an email address. |
| `POST` | `/api/v1/auth/password-reset/confirm` | Public | Reset password using a valid `reset_token` and strong `new_password`. |
| `POST` | `/api/v1/auth/staff` | `admin` | Create an `internal_staff` or `admin` user account. |
| `GET` | `/api/v1/auth/users` | `admin`, `internal_staff` | List registered user accounts (optional `role` filter). |

### 2.3 Customers (`/api/v1/customers`)
| Method | Path | Roles | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/customers` | Authenticated | List customers (`customer` role only sees their own record; supports `search` and `active_only`). |
| `POST` | `/api/v1/customers` | `admin`, `internal_staff` | Create a new B2B/B2C customer profile. |
| `GET` | `/api/v1/customers/{id}` | Authenticated (Owner/Staff) | Retrieve customer details. |
| `PUT` | `/api/v1/customers/{id}` | Authenticated (Owner/Staff) | Update customer contact, billing address, or tax ID. |
| `GET` | `/api/v1/customers/{id}/summary` | Authenticated (Owner/Staff) | Retrieve customer profile along with all their subscriptions, invoices, and total outstanding balance. |

### 2.4 Products & Variants (`/api/v1/products`)
| Method | Path | Roles | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/products` | Authenticated | List products with variants (supports `search`, `product_type`, `active_only`). |
| `POST` | `/api/v1/products` | `admin`, `internal_staff` | Create a product with optional initial variants. |
| `GET` | `/api/v1/products/{id}` | Authenticated | Retrieve product details and variants. |
| `PUT` | `/api/v1/products/{id}` | `admin`, `internal_staff` | Update product attributes, pricing, or active status. |
| `DELETE` | `/api/v1/products/{id}` | `admin` | Deactivate (`soft delete`) a product. |
| `POST` | `/api/v1/products/{id}/variants` | `admin`, `internal_staff` | Add a product variant with SKU and `additional_price`. |
| `PUT` | `/api/v1/products/variants/{variant_id}` | `admin`, `internal_staff` | Update a product variant. |

### 2.5 Subscription Plans (`/api/v1/plans`)
| Method | Path | Roles | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/plans` | Authenticated | List billing plans (filter by `billing_period`, `active_only`). |
| `POST` | `/api/v1/plans` | `admin`, `internal_staff` | Create a billing plan (`daily`, `weekly`, `monthly`, `yearly`). |
| `GET` | `/api/v1/plans/{id}` | Authenticated | Retrieve plan details. |
| `PUT` | `/api/v1/plans/{id}` | `admin`, `internal_staff` | Update plan parameters and lifecycle capabilities. |

### 2.6 Quotations & Templates (`/api/v1/quotations`)
| Method | Path | Roles | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/quotations/templates` | Authenticated | List reusable quotation templates. |
| `POST` | `/api/v1/quotations/templates` | `admin`, `internal_staff` | Create a quotation template. |
| `GET` | `/api/v1/quotations` | Authenticated (Scoped) | List quotations (filter by `status`, `customer_id`). |
| `POST` | `/api/v1/quotations` | `admin`, `internal_staff` | Create a quotation with product/variant lines, tax rules, and optional discount code. |
| `GET` | `/api/v1/quotations/{id}` | Authenticated (Owner/Staff) | Retrieve quotation details and calculated line totals. |
| `PUT` | `/api/v1/quotations/{id}` | `admin`, `internal_staff` | Update quotation lines, validity date, or status. |
| `POST` | `/api/v1/quotations/{id}/confirm` | Authenticated (Owner/Staff) | Confirm a quotation and atomically convert it into a `Subscription` (`confirmed` or immediately `active`). |

### 2.7 Subscriptions (`/api/v1/subscriptions`)
| Method | Path | Roles | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/subscriptions` | Authenticated (Scoped) | List subscriptions (filter by `status`, `customer_id`). |
| `POST` | `/api/v1/subscriptions` | `admin`, `internal_staff` | Create a subscription directly with line items. |
| `GET` | `/api/v1/subscriptions/{id}` | Authenticated (Owner/Staff) | Retrieve subscription details, lines, and billing schedule. |
| `PUT` | `/api/v1/subscriptions/{id}` | `admin`, `internal_staff` | Update subscription lines, payment terms, or dates. |
| `POST` | `/api/v1/subscriptions/{id}/transition` | Authenticated (Owner/Staff) | Execute lifecycle actions: `send_quotation`, `confirm`, `activate`, `pause`, `resume`, `mark_past_due`, `close`, `renew`. |

### 2.8 Invoices, Automated Billing, Discounts & Taxes (`/api/v1`)
| Method | Path | Roles | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/invoices` | Authenticated (Scoped) | List invoices (filter by `state`, `payment_status`, `customer_id`, `subscription_id`). |
| `POST` | `/api/v1/invoices` | `admin`, `internal_staff` | Create a manual or subscription-linked invoice. |
| `GET` | `/api/v1/invoices/{id}` | Authenticated (Owner/Staff) | Retrieve full invoice details, lines, and payment history. |
| `POST` | `/api/v1/invoices/{id}/transition` | `admin`, `internal_staff` | Confirm (`confirm`) or cancel (`cancel`) an invoice. |
| `GET` | `/api/v1/invoices/{id}/html` | Authenticated (Owner/Staff) | Render a print-ready HTML invoice document. |
| `GET` | `/api/v1/invoices/{id}/pdf` | Authenticated (Owner/Staff) | Download a binary PDF (`application/pdf`) invoice document. |
| `POST` | `/api/v1/invoices/billing/run` | `admin`, `internal_staff` | Trigger the idempotent automated recurring billing engine for `target_date`. |
| `GET` | `/api/v1/invoices/billing/jobs` | `admin`, `internal_staff` | List historical `BillingJob` execution logs. |
| `GET` | `/api/v1/discounts` | Authenticated | List promotional discounts. |
| `POST` | `/api/v1/discounts` | `admin`, `internal_staff` | Create a fixed or percentage discount with eligibility rules. |
| `PUT` | `/api/v1/discounts/{id}` | `admin`, `internal_staff` | Update a discount. |
| `POST` | `/api/v1/discounts/validate` | Authenticated | Validate a discount code against purchase subtotal, quantity, and product IDs. |
| `GET` | `/api/v1/tax-rules` | Authenticated | List configured tax rules. |
| `POST` | `/api/v1/tax-rules` | `admin`, `internal_staff` | Create a tax rule. |

### 2.9 Payments & Reconciliation (`/api/v1/payments`)
| Method | Path | Roles | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/payments` | Authenticated (Scoped) | List recorded payments (filter by `invoice_id`, `customer_id`). |
| `POST` | `/api/v1/payments` | Authenticated (Owner/Staff) | Record a full or partial payment against an invoice (with `idempotency_key`). |
| `GET` | `/api/v1/payments/invoices/{invoice_id}/balance` | Authenticated (Owner/Staff) | Retrieve real-time reconciliation breakdown (`grand_total`, `amount_paid`, `balance_due`, `is_overdue`, `days_overdue`). |
| `POST` | `/api/v1/payments/overdue-sweep` | `admin`, `internal_staff` | Scan all open invoices past their `due_date` and mark them `overdue` / subscriptions `past_due`. |

### 2.10 Finance Dashboard, Portal & Audit Reports (`/api/v1/reports`)
| Method | Path | Roles | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/reports/dashboard` | `admin`, `internal_staff` | Retrieve complete Finance Dashboard metrics (`start_date`, `end_date` filters). |
| `GET` | `/api/v1/reports/audit-logs` | `admin`, `internal_staff` | Retrieve immutable system audit logs (`entity_type` filter). |
| `GET` | `/api/v1/reports/customer-portal` | Authenticated | Retrieve unified self-service portal bundle for the logged-in customer. |

