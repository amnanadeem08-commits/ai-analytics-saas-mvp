# API Guide — v1.0 RC

Base URL: `/api/v1`

## Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Obtain bearer token |
| POST | `/auth/refresh` | Refresh access token |

Include header: `Authorization: Bearer <token>`

## Core Domains

- **Organizations** `/organizations`
- **Workspaces** `/workspaces`
- **RBAC** `/rbac`
- **Jobs** `/jobs` (supports `page`, `page_size`)
- **Storage** `/storage` (supports pagination; `?stream=true` on download)
- **Workflows** `/workflows`
- **Analyst** `/analyst`
- **Knowledge** `/knowledge`
- **Evaluation** `/evaluation`
- **Billing** `/billing`
- **API Keys** `/api-keys`
- **Admin** `/admin`

## Operations

- **Monitoring** `/monitoring/health`, `/metrics`, `/ready`, `/live`
- **Release** `/release/benchmarks`, `/release/validation`, `/release/security/audit`

## Version

Application version: `1.0.0` (see `/health`).
