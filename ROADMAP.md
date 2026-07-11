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
7. [ ] **UI polish** — incremental Streamlit UX improvements (no redesign required for 1.x)

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
- [ ] Next: Confirm v1.0.0 / beta on `release/1.0`

## Principles

- **v1.0 feature freeze:** `release/1.0` = bug fixes only; `develop` = future v1.1
- New features land on `develop` / `main` per operator branch policy
- Production hotfixes land on `release/1.0` and cherry-pick when appropriate
- SemVer: patch for fixes, minor for compatible features, major for breaking API changes
