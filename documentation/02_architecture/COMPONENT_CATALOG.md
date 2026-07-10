# Component Catalog

## API route modules (28)

| Module | Prefix (from source) | Mounted in main.py |
|--------|----------------------|--------------------|
| upload_routes | (upload) | Yes |
| dataset_routes | `/datasets` | Yes |
| analytics_routes | `/analytics` | Yes |
| insight_routes | `/insights` | Yes |
| intelligence_routes | `/intelligence` | Yes |
| visual_builder_routes | `/visual-builder` | Yes |
| report_routes | `/report` | Yes |
| theme_routes | `/themes` | Yes |
| branding_routes | `/branding` | Yes |
| sql_lab_routes | `/sql-lab` | Yes |
| dax_routes | `/dax` | Yes |
| system_routes | `/api/v1` | Yes |
| analyst_routes | `/api/v1` | Yes |
| workflow_routes | `/api/v1` | Yes |
| evaluation_routes | `/api/v1` | Yes |
| knowledge_routes | `/api/v1` | Yes |
| auth_routes | `/api/v1/auth` | Yes |
| organization_routes | `/api/v1/organizations` | Yes |
| workspace_routes | `/api/v1/workspaces` | Yes |
| rbac_routes | `/api/v1` | Yes |
| job_routes | `/api/v1/jobs` | Yes |
| storage_routes | `/api/v1/storage` | Yes |
| monitoring_routes | `/api/v1` | Yes |
| billing_routes | `/api/v1/billing` | Yes |
| apikey_routes | `/api/v1/api-keys` | Yes |
| admin_routes | `/api/v1/admin` | Yes |
| release_routes | `/api/v1/release` | Yes |
| rag_routes | `/rag` | **Not verified** (file exists; not in `create_app()` includes) |

## Service domains (selected)

See `backend/services/` for the full list of 89 `*_service.py` files spanning analytics, AI, forecast, commercial, and platform domains.
