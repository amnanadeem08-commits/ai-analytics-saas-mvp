# ROADMAP

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

1. **Billing gateway** — live payment provider integration
2. **Persistent commercial stores** — migrate in-memory billing/API-key stores to SQL
3. **S3 object storage** — production S3 provider beyond the stub
4. **Kubernetes / multi-node** — optional container orchestration profiles
5. **Enterprise SSO / IdP** — SAML/OIDC integrations
6. **Advanced forecasting plugins** — expanded model adapters
7. **UI polish** — incremental Streamlit UX improvements (no redesign required for 1.x)

## Principles

- New features land on `main`
- Production hotfixes land on `release/v1.0` and cherry-pick to `main` when appropriate
- SemVer: patch for fixes, minor for compatible features, major for breaking API changes
