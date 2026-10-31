# React Components

Shared components are grouped by UI responsibility and imported by route-level pages.

## Common UI — `common/`

The current common UI module [UI.jsx](common/UI.jsx) exports:

| Component | Responsibility |
|---|---|
| `StatusBadge` | Consistent visual treatment for roles and business statuses |
| `MetricCard` | KPI/summary card with optional icon and accent |
| `ToastBanner` | Success/error notification with dismiss action |
| `Modal` | Reusable dialog surface |
| `ConfirmDialog` | Confirmation dialog built on Modal |
| `LoadingState` | Loading indicator with contextual label |
| `EmptyState` | Empty-list guidance and optional action |

## Layout — `layout/`

[AppLayout.jsx](layout/AppLayout.jsx) provides the authenticated application shell: sidebar navigation, role-aware menu items, current-user identity, sign-out action, and the main content region.

## Tables — `tables/`

The tables directory contains reusable tabular UI used by domain pages. Keep column definitions and row-specific actions close to the page that owns the business workflow; keep generic table rendering reusable.

## Component conventions

- Prefer small components with explicit props.
- Keep API calls and domain workflows in pages/services rather than generic presentation components.
- Use accessible labels for buttons and form controls.
- Handle loading, empty, and error states explicitly.
- Keep role enforcement on the backend; conditional rendering is only a UI convenience.
