# ROADMAP

> **Mirror.** Canonical roadmap: [`pios/01_vision/ROADMAP.md`](pios/01_vision/ROADMAP.md)

## Released — v1.0.0

Stable production MVP covering analytics, AI analyst runtime, workflows, storage, monitoring, commercial controls, and production hardening.

## Maintenance — `release/v1.0`

Allowed on the maintenance branch:

- Bug fixes
- Security patches
- Documentation updates

Not allowed:

- Architectural changes
- Breaking API changes
- New product features

## Post-1.0 (main)

1. [x] **Billing gateway** — complete 2026-07-11
2. [x] **Persistent commercial stores** — complete 2026-07-11
3. [x] **S3 object storage** — complete 2026-07-11
4. [ ] **Kubernetes / multi-node** — optional container orchestration profiles
5. [ ] **Enterprise SSO / IdP** — SAML/OIDC integrations
6. [ ] **Advanced forecasting plugins** — expanded model adapters
7. [x] **UI polish** — Sprint 8.8 Streamlit UX (nav regroup, shared states, core flows) — **complete 2026-07-11**; Design System → Sprint 8.9
8. [x] **Product Design System (Sprint 8.9)** — tokens, type scale, reusable FE components — **complete 2026-07-11**
9. [ ] **Design system adoption** — migrate remaining admin/ops/auth pages to DS chrome

## Near-term engineering (active)

- [x] Phase 0.3: AI Business Column Suggestions — complete 2026-07-11
- [x] Billing gateway — complete 2026-07-11
- [x] Persistent commercial stores — complete 2026-07-11
- [x] S3 object storage — complete 2026-07-11
- [x] Production JWT fail-fast (KI-007) — complete 2026-07-11
- [x] Durable storage metadata (KI-009) — complete 2026-07-11
- [x] Production CORS hardening (KI-006) — complete 2026-07-11
- [x] TD-010 FE layer boundary — complete 2026-07-11
- [x] Production Docker Compose verification — complete 2026-07-11 (static; live on Docker host)
- [x] E2E smoke with real datasets — complete 2026-07-11
- [x] Branch cut: `release/1.0` + `develop` — complete 2026-07-11
- [x] Sprint 8.8 UX/UI polish (frontend-only) — complete 2026-07-11
- [x] Sprint 8.9 Product Design System — complete 2026-07-11
- [ ] Design system adoption (remaining pages)
- [ ] Ops: push branches, optional `v1.0.1` tag, live Compose, beta invite

## Principles

- **v1.0 feature freeze:** `release/1.0` = bug fixes only; `develop` = future v1.1
- New features land on `develop` / `main` per operator branch policy
- Production hotfixes land on `release/1.0` and cherry-pick when appropriate
- SemVer: patch for fixes, minor for compatible features, major for breaking API changes
