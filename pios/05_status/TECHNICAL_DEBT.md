# Technical Debt

Seeded from known issues and release limitations. Update via completion workflow.

| ID | Debt | Related KI | Priority | Notes |
|----|------|------------|----------|-------|
| TD-001 | Default commercial backend remains memory unless DB backend enabled | KI-002 | Medium | SQL path shipped; ops must enable `STORAGE_BACKEND`/`COMMERCIAL_STORAGE_BACKEND` |
| TD-002 | Live Stripe requires env secrets; internal gateway is default for local/dev | KI-001 | Medium | Gateway shipped; ops must configure Stripe for live charges |
| TD-003 | S3 storage implemented; ops must set bucket/creds | KI-003 | Low | Mitigated 2026-07-11 — use `OBJECT_STORAGE_BACKEND=s3` |
| TD-004 | No K8s manifests | KI-004 | Low | Compose sufficient for 1.x |
| TD-005 | No enterprise SSO | KI-005 | Medium | JWT local auth only |
| TD-006 | Permissive default CORS | KI-006 | **Mitigated** | Production fail-fast; localhost defaults in dev (2026-07-11) |
| TD-007 | Insecure default JWT secret | KI-007 | **Mitigated** | Production fail-fast + unified resolver (2026-07-11) |
| TD-008 | Pandas 4 `object` dtype deprecation warnings | KI-008 | Low | Patch cleanup |
| TD-009 | `/rag` mount verification gap | — | Low | Handbook: Not verified |
| TD-010 | `frontend/app_pages/ai_insights_page.py` imports `backend.services` | — | **Mitigated** | Local mode uses `backend.analytics`; API path remains HTTP (2026-07-11) |
| TD-011 | In-memory storage object metadata store | KI-009 | **Mitigated** | File + SQLAlchemy stores + auto migration (2026-07-11) |

## Policy

- Prefer documenting accepted MVP debt over silent workarounds
- **Feature development freeze for v1.0** — only production blockers / bug fixes on `release/1.0`
