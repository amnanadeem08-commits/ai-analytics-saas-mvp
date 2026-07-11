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

Planned on `main` after v1.0.0:

3. [x] **S3 object storage** — production S3 provider beyond the stub (**complete 2026-07-11**)
4. [ ] **Kubernetes / multi-node** — optional container orchestration profiles
5. [ ] **Enterprise SSO / IdP** — SAML/OIDC integrations
6. [ ] **Advanced forecasting plugins** — expanded model adapters
7. [ ] **UI polish** — incremental Streamlit UX improvements (no redesign required for 1.x)

## Near-term engineering (active)

- [x] Phase 0.3: AI Business Column Suggestions — complete 2026-07-11
- [x] Billing gateway — complete 2026-07-11
- [x] Persistent commercial stores — complete 2026-07-11
- [x] S3 object storage — complete 2026-07-11
- [ ] Next: Kubernetes or Enterprise SSO — see [`pios/01_vision/ROADMAP.md`](pios/01_vision/ROADMAP.md)

## Principles

- New features land on `main`
- Production hotfixes land on `release/v1.0` and cherry-pick to `main` when appropriate
- SemVer: patch for fixes, minor for compatible features, major for breaking API changes
