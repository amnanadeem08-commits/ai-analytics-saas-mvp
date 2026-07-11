# Technical Debt

Seeded from known issues and release limitations. Update via completion workflow.

| ID | Debt | Related KI | Priority | Notes |
|----|------|------------|----------|-------|
| TD-001 | Default commercial backend remains memory unless DB backend enabled | KI-002 | Medium | SQL path shipped; ops must enable `STORAGE_BACKEND`/`COMMERCIAL_STORAGE_BACKEND` |
| TD-002 | Live Stripe requires env secrets; internal gateway is default for local/dev | KI-001 | Medium | Gateway shipped; ops must configure Stripe for live charges |
| TD-003 | S3 storage implemented; ops must set bucket/creds | KI-003 | Low | Mitigated 2026-07-11 — use `OBJECT_STORAGE_BACKEND=s3` |
| TD-004 | No K8s manifests | KI-004 | Low | Compose sufficient for 1.x |
| TD-005 | No enterprise SSO | KI-005 | Medium | JWT local auth only |
| TD-006 | Permissive default CORS | KI-006 | Medium (ops) | Env harden in prod |
| TD-007 | Insecure default JWT secret in example | KI-007 | High (ops) | Operator checklist |
| TD-008 | Pandas 4 `object` dtype deprecation warnings | KI-008 | Low | Patch cleanup |
| TD-009 | `/rag` mount verification gap | — | Low | Handbook: Not verified |
| TD-010 | `frontend/app_pages/ai_insights_page.py` imports `backend.services` | — | Medium | Violates FE_NO_BACKEND_SERVICES; route via API client |

## Policy

- Prefer documenting accepted MVP debt over silent workarounds
- Paying down TD-001/TD-002 unlocks commercial durability
