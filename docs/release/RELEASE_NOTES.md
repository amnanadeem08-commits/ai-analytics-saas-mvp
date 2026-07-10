# Release Notes — Data Bot AI v1.0.0

**Official Production Release — 2026-07-10**

## Summary

Data Bot AI **v1.0.0** is the first stable production release. It includes the complete analytics platform, AI analyst runtime, workflows, storage, monitoring, commercial controls, and Sprint 8.7 production hardening.

## What's Included

- Dataset upload, cleaning, analytics dashboards, and visual exports
- AI Analyst workspace, workflows, evaluation, and knowledge/RAG
- Authentication, organizations, workspaces, RBAC
- Async jobs and optional background workers
- Object storage lifecycle (local provider)
- Monitoring, health, metrics, and structured logging
- Billing plans, usage quotas, API keys, and admin surfaces
- Performance, security, and reliability production layers
- Release validation endpoints under `/api/v1/release/*`

## Version

`1.0.0` (promoted from `1.0.0-rc.1`)

## Documentation

- [Architecture Guide](docs/release/ARCHITECTURE_GUIDE.md)
- [Deployment Guide](docs/release/DEPLOYMENT_GUIDE.md)
- [API Guide](docs/release/API_GUIDE.md)
- [Security Guide](docs/release/SECURITY_GUIDE.md)
- [Disaster Recovery Guide](docs/release/DISASTER_RECOVERY_GUIDE.md)
- [CHANGELOG](../CHANGELOG.md)
- [ROADMAP](../ROADMAP.md)
- [Known Issues](../KNOWN_ISSUES.md)

## Maintenance

Hotfixes: branch `release/v1.0` (bug fixes, security patches, docs only).  
New features: continue on `main`.

## Known Limitations

See [KNOWN_ISSUES.md](../KNOWN_ISSUES.md).
