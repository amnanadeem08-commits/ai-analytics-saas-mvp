# Sprint Archive — Persistent Commercial Stores (Post-1.0 #2)

Completed 2026-07-11.

- Commercial repository seam (memory default, SQL when database backend enabled)
- Tables: subscriptions, invoices, credits, payments, usage, api_keys
- Alembic: `a1b2c3d4e5f6_commercial_stores`
- Services wired through `get_commercial_stores()`
