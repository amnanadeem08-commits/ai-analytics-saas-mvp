# CHANGELOG

All notable changes to Data Bot AI are documented in this file.

## [1.0.0] — 2026-07-10

### Official Production Release

First stable production release of Data Bot AI.

### Added

- Authentication, organizations, workspaces, and RBAC
- Async jobs and background workers
- Dataset persistence, object storage, and file lifecycle
- Production monitoring, health probes, and observability
- Commercial platform: billing plans, usage quotas, API keys, admin
- Performance layer: caching, pagination, compression, streaming downloads
- Security hardening: headers, CORS, rate limiting, CSRF, brute-force protection
- Reliability: graceful shutdown, circuit breakers, retries, timeouts, fallbacks
- Release validation and benchmark endpoints (`/api/v1/release/*`)
- Complete operations documentation and v1.0 release checklists

### Changed

- Application version locked at `1.0.0`
- CORS credentials disabled when origins are wildcard
- Job and storage list APIs support pagination

### Known Limitations

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## [1.0.0-rc.1] — 2026-07-10

Production Release Candidate (Sprint 8.7) — performance, security, reliability, load tests, and release documentation.

## Earlier

Sprints 0–8.6 delivered core analytics, AI analyst runtime, workflows, evaluation, knowledge/RAG, forecasting, infrastructure, and commercial platform foundations.
