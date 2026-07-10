# 09 — API Handbook

Base application: FastAPI (`backend/main.py`).
Legacy product routes often lack `/api/v1` prefix; platform routes use `/api/v1`.

OpenAPI UI: `/docs` when server is running (**verified FastAPI default**).

## Authentication

- Register/login under `/api/v1/auth`
- Send `Authorization: Bearer <access_token>` for protected routes
- CSRF optional via `CSRF_ENABLED` + `X-CSRF-Token`

## Endpoint inventory (auto-extracted decorators)

### `admin_routes.py` — prefix `/api/v1/admin`

- `GET` `/api/v1/admin/dashboard`
- `GET` `/api/v1/admin/statistics`
- `GET` `/api/v1/admin/users`
- `GET` `/api/v1/admin/organizations`
- `GET` `/api/v1/admin/workspaces`
- `GET` `/api/v1/admin/subscriptions`
- `GET` `/api/v1/admin/api-keys`
- `GET` `/api/v1/admin/usage`
- `GET` `/api/v1/admin/audit`
- `GET` `/api/v1/admin/invoices`
- `GET` `/api/v1/admin/features`
- `PUT` `/api/v1/admin/features/{feature_key}`

### `analyst_routes.py` — prefix `/api/v1`

- `POST` `/api/v1/analyst/analyze`
- `POST` `/api/v1/session/create`
- `GET` `/api/v1/session/{session_id}`
- `GET` `/api/v1/session/{session_id}/summary`
- `GET` `/api/v1/session/{session_id}/evaluation`
- `POST` `/api/v1/session/{session_id}/execute`

### `analytics_routes.py` — prefix `/analytics`

- `GET` `/analytics/{dataset_id}/summary`
- `GET` `/analytics/{dataset_id}/dashboard`
- `POST` `/analytics/{dataset_id}/dashboard/filter`

### `apikey_routes.py` — prefix `/api/v1/api-keys`

- `POST` `/api/v1/api-keys`
- `GET` `/api/v1/api-keys`
- `GET` `/api/v1/api-keys/{key_id}`
- `DELETE` `/api/v1/api-keys/{key_id}`
- `POST` `/api/v1/api-keys/{key_id}/rotate`

### `auth_routes.py` — prefix `/api/v1/auth`

- `POST` `/api/v1/auth/register`
- `POST` `/api/v1/auth/login`
- `POST` `/api/v1/auth/refresh`
- `POST` `/api/v1/auth/logout`
- `POST` `/api/v1/auth/change-password`
- `POST` `/api/v1/auth/request-password-reset`
- `POST` `/api/v1/auth/reset-password`
- `POST` `/api/v1/auth/verify-email`
- `GET` `/api/v1/auth/me`
- `PUT` `/api/v1/auth/me/profile`
- `GET` `/api/v1/auth/sessions`

### `billing_routes.py` — prefix `/api/v1/billing`

- `GET` `/api/v1/billing/plans`
- `GET` `/api/v1/billing/plans/{plan_id}`
- `GET` `/api/v1/billing/subscriptions/{organization_id}`
- `POST` `/api/v1/billing/subscriptions/{organization_id}`
- `POST` `/api/v1/billing/subscriptions/{organization_id}/upgrade`
- `POST` `/api/v1/billing/subscriptions/{organization_id}/downgrade`
- `POST` `/api/v1/billing/subscriptions/{organization_id}/suspend`
- `POST` `/api/v1/billing/subscriptions/{organization_id}/reactivate`
- `GET` `/api/v1/billing/usage/{organization_id}`
- `GET` `/api/v1/billing/usage/{organization_id}/records`
- `GET` `/api/v1/billing/limits/{organization_id}`
- `GET` `/api/v1/billing/estimate/{organization_id}`
- `POST` `/api/v1/billing/invoices/{organization_id}`
- `GET` `/api/v1/billing/invoices/{organization_id}`
- `GET` `/api/v1/billing/invoices/detail/{invoice_id}`
- `GET` `/api/v1/billing/credits/{organization_id}`
- `POST` `/api/v1/billing/credits/{organization_id}`

### `branding_routes.py` — prefix `/branding`

- `GET` `/branding`
- `PUT` `/branding`
- `POST` `/branding/logo`
- `GET` `/branding/logo/current`

### `dataset_routes.py` — prefix `/datasets`

- `GET` `/datasets`
- `GET` `/datasets/{dataset_id}`
- `GET` `/datasets/{dataset_id}/status`
- `GET` `/datasets/{dataset_id}/overview`
- `GET` `/datasets/{dataset_id}/preview`
- `POST` `/datasets/{dataset_id}/clean`
- `GET` `/datasets/{dataset_id}/clean/download`

### `dax_routes.py` — prefix `/dax`

- `GET` `/dax/{dataset_id}/library`
- `POST` `/dax/{dataset_id}/generate`
- `POST` `/dax/explain`
- `POST` `/dax/optimize`
- `POST` `/dax/{dataset_id}/optimize`
- `POST` `/dax/detect-errors`

### `evaluation_routes.py` — prefix `/api/v1`

- `POST` `/api/v1/evaluation/run`
- `GET` `/api/v1/evaluation/session/{session_id}`
- `GET` `/api/v1/evaluation/workflow/{workflow_id}`
- `GET` `/api/v1/evaluation/report/{evaluation_id}`
- `GET` `/api/v1/evaluation/export/{evaluation_id}`

### `insight_routes.py` — prefix `/insights`

- `GET` `/insights/{dataset_id}`
- `GET` `/insights/{dataset_id}/decision-framework`
- `POST` `/insights/{dataset_id}/ask`

### `intelligence_routes.py` — prefix `/intelligence`

- `GET` `/intelligence/{dataset_id}/data-insights`
- `GET` `/intelligence/{dataset_id}/ai-business-insights`
- `GET` `/intelligence/{dataset_id}/executive-storyboard`
- `GET` `/intelligence/{dataset_id}/domain`
- `GET` `/intelligence/{dataset_id}/regional`

### `job_routes.py` — prefix `/api/v1/jobs`

- `POST` `/api/v1/jobs`
- `GET` `/api/v1/jobs/statistics`
- `GET` `/api/v1/jobs`
- `GET` `/api/v1/jobs/{job_id}`
- `DELETE` `/api/v1/jobs/{job_id}`
- `POST` `/api/v1/jobs/{job_id}/retry`

### `knowledge_routes.py` — prefix `/api/v1`

- `POST` `/api/v1/knowledge/ingest`
- `POST` `/api/v1/knowledge/search`
- `GET` `/api/v1/knowledge/documents`
- `DELETE` `/api/v1/knowledge/{document_id}`

### `monitoring_routes.py` — prefix `/api/v1`

- `GET` `/api/v1/monitoring/health`
- `GET` `/api/v1/ready`
- `GET` `/api/v1/live`
- `GET` `/api/v1/metrics`
- `GET` `/api/v1/system/status`
- `GET` `/api/v1/system/config`
- `GET` `/api/v1/system/dependencies`

### `organization_routes.py` — prefix `/api/v1/organizations`

- `POST` `/api/v1/organizations`
- `GET` `/api/v1/organizations`
- `GET` `/api/v1/organizations/{organization_id}`
- `PUT` `/api/v1/organizations/{organization_id}`
- `DELETE` `/api/v1/organizations/{organization_id}`
- `POST` `/api/v1/organizations/{organization_id}/restore`
- `POST` `/api/v1/organizations/{organization_id}/invite`
- `POST` `/api/v1/organizations/invitations/accept`
- `POST` `/api/v1/organizations/invitations/decline`
- `GET` `/api/v1/organizations/{organization_id}/members`
- `DELETE` `/api/v1/organizations/{organization_id}/members/{member_user_id}`
- `POST` `/api/v1/organizations/{organization_id}/transfer-ownership`

### `rag_routes.py` — prefix `/rag`

- `POST` `/rag/{dataset_id}/index`
- `GET` `/rag/{dataset_id}/status`
- `POST` `/rag/{dataset_id}/retrieve`
- `DELETE` `/rag/{dataset_id}/index`

### `rbac_routes.py` — prefix `/api/v1`

- `GET` `/api/v1/roles`
- `GET` `/api/v1/permissions`
- `POST` `/api/v1/roles/assign`
- `POST` `/api/v1/roles/remove`
- `GET` `/api/v1/access/check`

### `release_routes.py` — prefix `/api/v1/release`

- `GET` `/api/v1/release/benchmarks`
- `GET` `/api/v1/release/validation`
- `GET` `/api/v1/release/security/audit`
- `GET` `/api/v1/release/recovery`
- `GET` `/api/v1/release/performance`

### `report_routes.py` — prefix `/report`

- `GET` `/report/{dataset_id}`
- `GET` `/report/{dataset_id}/export`

### `sql_lab_routes.py` — prefix `/sql-lab`

- `GET` `/sql-lab/{dataset_id}/templates`
- `GET` `/sql-lab/{dataset_id}/history`
- `POST` `/sql-lab/{dataset_id}/query`
- `POST` `/sql-lab/{dataset_id}/generate`
- `POST` `/sql-lab/{dataset_id}/save`
- `POST` `/sql-lab/explain`
- `POST` `/sql-lab/optimize`
- `POST` `/sql-lab/detect-errors`

### `storage_routes.py` — prefix `/api/v1/storage`

- `POST` `/api/v1/storage/upload`
- `GET` `/api/v1/storage/files`
- `GET` `/api/v1/storage/statistics`
- `GET` `/api/v1/storage/{object_id}`
- `GET` `/api/v1/storage/{object_id}/download`
- `DELETE` `/api/v1/storage/{object_id}`
- `POST` `/api/v1/storage/{object_id}/archive`
- `POST` `/api/v1/storage/{object_id}/restore`
- `POST` `/api/v1/storage/{object_id}/rollback`
- `POST` `/api/v1/storage/{object_id}/verify`

### `system_routes.py` — prefix `/api/v1`

- `GET` `/api/v1/health`
- `GET` `/api/v1/version`
- `GET` `/api/v1/capabilities`

### `theme_routes.py` — prefix `/themes`

- `GET` `/themes`
- `GET` `/themes/active`
- `POST` `/themes/active/{theme_name}`

### `upload_routes.py` — prefix ``

- `POST` `/upload`

### `visual_builder_routes.py` — prefix `/visual-builder`

- `GET` `/visual-builder/{dataset_id}/schema`
- `POST` `/visual-builder/{dataset_id}/render`
- `POST` `/visual-builder/{dataset_id}/register`

### `workflow_routes.py` — prefix `/api/v1`

- `POST` `/api/v1/workflow/execute`
- `GET` `/api/v1/workflow/status/{execution_id}`
- `GET` `/api/v1/workflow/results/{execution_id}`
- `GET` `/api/v1/workflow/statistics`

### `workspace_routes.py` — prefix `/api/v1/workspaces`

- `POST` `/api/v1/workspaces`
- `GET` `/api/v1/workspaces`
- `GET` `/api/v1/workspaces/{workspace_id}`
- `PUT` `/api/v1/workspaces/{workspace_id}`
- `DELETE` `/api/v1/workspaces/{workspace_id}`
- `POST` `/api/v1/workspaces/{workspace_id}/restore`
- `GET` `/api/v1/workspaces/{workspace_id}/members`

## Best practices

- Prefer `/api/v1` gateway for new integrations
- Handle 401/403/429 (auth + rate limit + lockout)
- Paginate jobs/storage lists with `page` & `page_size`
- Use `/api/v1/release/validation` after deploy

## Errors

Mapped via `backend/api/error_handlers.py` and service exceptions (`AuthError`, `JobError`, `StorageError`, etc.).
