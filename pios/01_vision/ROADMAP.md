# ROADMAP (canonical)

> Canonical live roadmap. Root [`ROADMAP.md`](../../ROADMAP.md) mirrors this file.

## Released — v1.0.0

Stable production MVP covering analytics, AI analyst runtime, workflows, storage, monitoring, commercial controls, and production hardening.

## Maintenance — `release/v1.0`

Allowed:

- Bug fixes
- Security patches
- Documentation updates

Not allowed:

- Architectural changes
- Breaking API changes
- New product features

## Post-1.0 (main)

1. [x] **Billing gateway** — live payment provider integration (**complete 2026-07-11**)
2. [x] **Persistent commercial stores** — migrate in-memory billing/API-key stores to SQL (**complete 2026-07-11**)
3. [x] **S3 object storage** — production S3 provider beyond the stub (**complete 2026-07-11**)
4. [ ] **Kubernetes / multi-node** — optional container orchestration profiles
5. [ ] **Enterprise SSO / IdP** — SAML/OIDC integrations
6. [ ] **Advanced forecasting plugins** — expanded model adapters
7. [ ] **UI polish** — incremental Streamlit UX improvements (no redesign required for 1.x)

## Near-term engineering (active)

- [x] Phase 0.3: AI Business Column Suggestions (local session) — **complete 2026-07-11**
- [x] Billing gateway — **complete 2026-07-11**
- [x] Persistent commercial stores — **complete 2026-07-11**
- [x] S3 object storage — **complete 2026-07-11**
- [x] Production JWT fail-fast (KI-007) — **complete 2026-07-11**
- [x] Durable storage metadata (KI-009) — **complete 2026-07-11**
- [x] Production CORS hardening (KI-006) — **complete 2026-07-11**
- [x] TD-010 FE layer boundary — **complete 2026-07-11**
- [x] Production Docker Compose verification — **complete 2026-07-11** (static; live on Docker host)
- [x] E2E smoke with real datasets — **complete 2026-07-11**
- [x] Branch cut: `release/1.0` + `develop` — **complete 2026-07-11**
- [ ] Ops: push branches, optional `v1.0.1` tag, live Compose, beta invite

## Principles

- **v1.0 feature freeze:** new product features land on `develop` for v1.1; `release/1.0` accepts bug fixes / security only
- New features land on `main` / `develop` after freeze policy is applied by operators
- Production hotfixes land on `release/1.0` and cherry-pick to `main` when appropriate
- SemVer: patch for fixes, minor for compatible features, major for breaking API changes
