# PIOS Changelog

Agent-facing change log. Product release history also lives in root [`CHANGELOG.md`](../CHANGELOG.md).

## [Unreleased] — post-1.0.0 engineering

### 2026-07-11 — Persistent commercial stores complete

#### Added

- Commercial repository layer (memory + SQLAlchemy) for subscriptions, invoices, credits, payments, usage, API keys
- Alembic migration `a1b2c3d4e5f6_commercial_stores`
- `COMMERCIAL_STORAGE_BACKEND` override (else follows `STORAGE_BACKEND`)

### 2026-07-11 — Billing gateway complete

#### Added

- Payment gateway providers (`internal`, `stripe`) under `backend/services/payment_gateway/`
- Checkout + webhook APIs under `/api/v1/billing/payments/*` and `/api/v1/billing/webhooks/{provider}`
- Billing dashboard pay/checkout controls
- Env: `BILLING_GATEWAY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`

#### Notes

- Product version remains `1.0.0`
- In-memory commercial stores still apply (TD-001)

### 2026-07-11 — Phase 0.3 complete

#### Added / Verified

- AI Business Column Suggestions (local session): recipe registry, detection, preview, explicit create
- `frontend/services/business_columns_service.py`
- `tests/test_business_columns_service.py` (20 tests)
- Dataset Data Quality Workspace UI wiring in `frontend/app_pages/dataset_page.py`
- PIOS control plane (`pios/`) established as agent SSOT

#### Notes

- Product version remains `1.0.0`
- Arch rule FE_NO_BACKEND_SERVICES still fails on legacy TD-010 (`ai_insights_page.py`)

## [1.0.0] — 2026-07-10

See root `CHANGELOG.md` for the official production release notes.
