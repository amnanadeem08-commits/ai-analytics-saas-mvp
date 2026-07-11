# Sprint Archive — Billing Gateway (Post-1.0 #1)

Completed 2026-07-11.

- Provider pattern: internal + Stripe (HTTPS, no stripe SDK)
- Checkout + webhook settlement for invoices
- Default remains `BILLING_GATEWAY=internal` for local/tests
- Live Stripe requires `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET`
