# Sprint Archive — 6.x → 8.7 → 1.0.0

> Historical summary. Exact calendar dates: **Not verified**.  
> Source: [`documentation/14_sprints/README.md`](../../documentation/14_sprints/README.md)

| Sprint | Goal | Architecture impact | Business value |
|--------|------|---------------------|----------------|
| 6.x–7.x | Analytics + AI foundations | Datasets, dashboards, insights, early AI | Core analyst product |
| 7.7–7.8 | Analyst runtime + `/api/v1` gateway | Workflows, evaluation, knowledge APIs | Production API surface |
| 8.0 | Authentication | JWT identity | Secure access |
| 8.1 | Orgs / workspaces / RBAC | Multi-tenant authorization | Team collaboration |
| 8.2 | SQLAlchemy persistence | Repositories + Alembic | Durable platform data |
| 8.3 | Jobs / queue / workers | Async execution | Long-running work |
| 8.4 | Storage lifecycle | Object storage abstraction | Dataset/artifact durability |
| 8.5 | Monitoring & config | Health, metrics, logging, docker | Operability |
| 8.6 | Commercial platform | Billing, usage, API keys, admin | Monetization controls |
| 8.7 | Production RC hardening | Performance, security, reliability, load tests, docs | Release readiness |
| **1.0.0** | Official release | Tag `v1.0.0`, maintenance branch | Production declaration |

## Lessons learned

- Keep services behind interfaces (repos, storage, queue) for swap-outs
- In-memory MVP stores ship faster but must be documented as limitations
- Release gates (tests + E2E + checklists) beat feature count for production trust
