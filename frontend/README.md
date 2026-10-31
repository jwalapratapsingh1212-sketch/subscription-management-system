# Frontend

The frontend is a React 18 single-page application built with Vite. It uses React Router for navigation, Axios for API calls, Tailwind CSS for styling, Lucide icons, and Recharts for data visualization.

## Requirements

- Node.js with npm.
- A running backend API, unless using a configured remote API URL.

## Install and run

From the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Vite prints the local development URL (commonly `http://localhost:5173`). Build and preview the production bundle with:

```powershell
npm run build
npm run preview
```

## API configuration

The Axios client reads `VITE_API_BASE_URL`. If it is not set, it uses the relative path `/api/v1`. Configure the development proxy or deployment routing so that this path reaches the FastAPI service. Do not put server-side secrets in Vite environment variables; values prefixed with `VITE_` are exposed to the browser bundle.

## Main areas

- Login, customer self-registration, and password reset.
- Staff dashboard and customer management.
- Products, product variants, and subscription plans.
- Quotations and subscription lifecycle management.
- Invoices, discounts, tax rules, and payment recording.
- Customer self-service portal.

## Role-aware navigation

The app uses an authentication context. Staff/admin users see the operations workspace; customer users are routed to the customer portal. Route guards are implemented in [src/App.jsx](src/App.jsx), and the sidebar/navigation shell is in [src/components/layout/AppLayout.jsx](src/components/layout/AppLayout.jsx).

## Source map

See [src/README.md](src/README.md) for the entrypoint, route map, shared components, pages, and API service structure.

**Verification status:** The commands match the checked-in package scripts. A successful production build has not been asserted by this document.
