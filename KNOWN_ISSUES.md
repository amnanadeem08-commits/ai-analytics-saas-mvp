# Known Issues — Data Bot AI v1.0.0

Formally documented limitations for the v1.0.0 production release. None of these block release; they are accepted MVP constraints.

| ID | Area | Issue | Severity | Status | Mitigation / Plan |
|----|------|-------|----------|--------|-------------------|
| KI-001 | Billing | No live payment gateway | Medium | Accepted | Manual invoices + credits; gateway planned post-1.0 |
| KI-002 | Persistence | Billing, usage, API keys, and some auth stores are in-memory | Medium | Accepted | Restart clears commercial state; SQL migration on roadmap |
| KI-003 | Storage | S3 provider is a stub; local filesystem is production path for MVP | Low | Accepted | Use `STORAGE_BACKEND=local`; S3 completion post-1.0 |
| KI-004 | Deploy | No Kubernetes manifests | Low | Accepted | Docker Compose + process manager; K8s out of scope for 1.0 |
| KI-005 | Integrations | No enterprise SSO / IdP | Low | Accepted | Local JWT auth; SSO on roadmap |
| KI-006 | CORS | Default `CORS_ALLOWED_ORIGINS=*` is permissive for local/dev | Medium | Accepted | Restrict origins in production via env (see Configuration Guide) |
| KI-007 | Secrets | Default `JWT_SECRET` in `.env.example` is insecure | High (ops) | Documented | Operators must set a ≥32-char secret before production deploy |
| KI-008 | Pandas | `select_dtypes(include=["object"])` emits Pandas 4 deprecation warnings | Low | Accepted | Non-blocking; cleanup planned as a patch |

## Release Gate Decision

All KI items above are **formally accepted** for v1.0.0. Security-critical operational items (KI-006, KI-007) are covered by deployment and configuration checklists and must be addressed in the target environment before go-live.
