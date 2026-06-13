# AI Analytics App Brainstorm + Requirements

Source reviewed: `D:\ai_analytics_platform\ai_analytics_platform`

Target app: `D:\ai-analytics-saas-mvp`

## Product Direction

Build this MVP from a simple CSV analytics app into a practical AI analytics platform:

1. Upload CSV/Excel data.
2. Persist datasets so they survive backend restart.
3. Detect schema, column types, business domain, and data quality.
4. Generate KPI cards, charts, dashboards, maps, and insights automatically.
5. Let users ask questions in natural language.
6. Add visual builder controls for user-created charts.
7. Export executive reports as PDF, PPTX, or Excel.

## Existing MVP Strengths

The current repo already has the right foundation:

- FastAPI backend in `backend/main.py`
- Route/service split under `backend/api/routes` and `backend/services`
- CSV upload, preview, summary, dashboard, insights, and ask-question flow
- Streamlit UI in `frontend/streamlit_app.py`
- Simple local metadata store under `data/metadata`

Keep this structure. Add features in small layers instead of replacing the app.

## Best Functions To Take From The Larger Platform

### 1. Dataset Record + Persistence

Take ideas from:

- `backend/core/dataset.py`
- `backend/core/dataset_registry.py`
- `backend/core/dataset_lifecycle.py`
- `backend/core/file_storage.py`
- `backend/core/job_store.py`

Useful behavior:

- `DatasetRecord` dataclass with raw data, cleaned data, schema, overview, status, parent id, and created time.
- Save uploaded datasets as `data.parquet` plus `meta.json`.
- Load persisted datasets on startup.
- Track lifecycle status: `uploading`, `processing`, `ready`, `failed`.
- Use file hashes to invalidate caches and reports.

MVP adaptation:

- Add parquet persistence after upload.
- Keep current JSON metadata, but enrich it with schema, overview, status, and file hash.
- Add `/datasets/{dataset_id}/status`.

### 2. Schema + Overview Brain

Take ideas from:

- `backend/services/processing/schema_service.py`
- `backend/services/processing/overview_service.py`
- `backend/services/upload/ingestion_service.py`

Useful behavior:

- Support CSV and Excel upload.
- Build column schema with semantic type.
- Build overview with row count, column count, preview, missing summary, column groups, memory size, and AI context.

MVP adaptation:

- Expand current CSV loader to support `.xlsx`.
- Return a richer upload response.
- Store column groups as `numeric`, `categorical`, `datetime`, `boolean`, and `geo`.

### 3. Dashboard + KPI Engine

Take ideas from:

- `backend/services/analytics/dashboard_service.py`
- `backend/services/analytics/kpi_engine.py`
- `backend/services/analytics/kpi_domain.py`
- `backend/services/analytics/kpi_trend_engine.py`
- `backend/schemas/dashboard.py`

Useful behavior:

- `build_dashboard(record, mode)` creates one dashboard view model.
- `compute_dashboard_kpis(...)` creates typed KPI cards.
- Semantic KPI detection: revenue, sales, profit, cost, age, sleep, stress, churn, tenure.
- Business/research modes filter what KPIs matter.
- KPI cards include trend, direction, sentiment, sparkline, and period label.

MVP adaptation:

- Replace the current basic dashboard response with a richer `DashboardView`.
- Start with business mode only.
- Add research mode later.

### 4. Chart Brain

Take ideas from:

- `backend/services/analytics/chart_engine.py`
- `backend/core/chart_engine/generators.py`
- `backend/core/chart_engine/chart_schema.py`

Useful behavior:

- Auto-generate Plotly chart specs from schema.
- Generate histograms, categorical bars, pies, comparison bars, trends, scatter plots, and correlation heatmaps.
- Group charts into sections: trends, distributions, comparisons, relationships, geography.

MVP adaptation:

- Add `/analytics/{dataset_id}/dashboard` or enhance current dashboard endpoint.
- Return chart specs from backend, render them in Streamlit.
- Use Plotly dependency.

### 5. Decision Intelligence / Insights

Take ideas from:

- `backend/services/analytics/insight_intelligence_service.py`
- `backend/services/analytics/decision_intelligence_orchestrator.py`
- `backend/services/analytics/ceo_brief_engine.py`
- `backend/schemas/intelligence.py`

Useful behavior:

- Generate grounded Insight / Reason / Action briefs.
- Detect domains like churn, ecommerce, health, and generic business.
- Evidence-first insights from computed metrics.
- Confidence based on row count and completeness.

MVP adaptation:

- Upgrade current rule-based insight service to return:
  - `insight`
  - `reason`
  - `action`
  - `evidence`
  - `metrics_snapshot`
  - `confidence`

### 6. Natural Language Analyst

Take ideas from:

- `backend/analyst_engine/orchestrator.py`
- `backend/analyst_engine/intent_engine.py`
- `backend/analyst_engine/query_planner.py`
- `backend/analyst_engine/sql_generator.py`
- `backend/analyst_engine/response_engine.py`
- `backend/analyst_engine/cohort_memory.py`
- `backend/api/routes/chat.py`
- `backend/api/routes/ai_routes.py`

Useful behavior:

- Pipeline: intent detection, cohort memory, query plan, SQL generation, response formatting.
- Fallback rule-based behavior without LLM.
- Cohort memory for follow-up questions like "now only show the west region".
- Human-readable answer plus structured UI sections.

MVP adaptation:

- Keep current `ask_question` endpoint for now.
- Add an internal intent parser and simple pandas/SQL executor.
- Later add `/chat/{dataset_id}` with conversation context.

### 7. Visual Builder

Take ideas from:

- `backend/services/analytics/visual_builder_service.py`
- `backend/services/analytics/visual_mapping_engine.py`
- `backend/api/routes/visual_builder.py`
- `ui/components/visual_builder_panel.py`

Useful behavior:

- Discover fields as dimensions, measures, dates, categories.
- Suggest chart type from selected shelves.
- Render a user-defined chart with filters.

MVP adaptation:

- Add a Streamlit "Visual Builder" page.
- Users choose x, y, aggregation, chart type, filters.
- Backend returns Plotly chart JSON.

### 8. Filtering + Interactive Dashboard

Take ideas from:

- `backend/core/data_engine/dataframe_manager.py`
- `backend/core/data_engine/filter_engine.py`
- `backend/core/data_engine/filter_schema.py`
- `backend/services/analytics/interactive_dashboard_service.py`
- `backend/api/routes/dashboard.py`

Useful behavior:

- Dataset-bound DataFrame manager.
- Filter options per column.
- Rebuild dashboard from filtered data.

MVP adaptation:

- Add filters to dashboard endpoint as query/body payload.
- Start with categorical multi-select and date range.

### 9. Report Export

Take ideas from:

- `backend/services/analytics/pdf_report_generator.py`
- `backend/services/analytics/ppt_report_generator.py`
- `backend/services/analytics/report_export_service.py`
- `backend/api/routes/report.py`

Useful behavior:

- Export dashboard and insights to PDF/PPTX.
- Cache generated report files.
- Add charts to a report builder.

MVP adaptation:

- Start with one PDF executive summary.
- Add PPTX after dashboard chart specs are stable.

## Dependencies To Add

Current MVP dependencies are minimal. The larger platform uses:

- `numpy`
- `plotly`
- `openpyxl`
- `duckdb`
- `pandasql`
- `reportlab`
- `python-pptx`
- `python-dotenv`
- optional `anthropic`

Recommended first dependency upgrade:

```text
numpy
plotly
openpyxl
pyarrow
```

Recommended later:

```text
duckdb
reportlab
python-pptx
python-dotenv
```

Do not add LLM dependency until the rule-based app is strong.

## New API Requirements

Suggested endpoints for this MVP:

- `POST /upload` - keep, but support CSV and Excel.
- `GET /datasets` - keep.
- `GET /datasets/{dataset_id}` - full overview.
- `GET /datasets/{dataset_id}/status` - lifecycle/status.
- `GET /analytics/{dataset_id}/summary` - keep.
- `GET /analytics/{dataset_id}/dashboard` - KPI cards, chart specs, intelligence brief.
- `POST /analytics/{dataset_id}/dashboard/filter` - filtered dashboard.
- `GET /insights/{dataset_id}` - upgraded Insight/Reason/Action.
- `POST /insights/{dataset_id}/ask` - current NL question flow.
- `POST /chat/{dataset_id}` - later full analyst chat.
- `GET /visual-builder/{dataset_id}/schema` - visual builder fields.
- `POST /visual-builder/{dataset_id}/render` - custom chart.
- `GET /report/{dataset_id}/pdf` - executive PDF.

## Implementation Phases

### Phase 1: Solid Dataset Foundation

- Add dataset persistence.
- Add richer schema and overview.
- Add Excel upload.
- Add lifecycle/status response.

### Phase 2: Better Dashboard

- Add KPI card schema.
- Add Plotly chart spec schema.
- Add dashboard view model.
- Render KPI cards and chart sections in Streamlit.

### Phase 3: Better Insight Brain

- Add domain detection.
- Add Insight / Reason / Action output.
- Add evidence and confidence.
- Keep rule-based fallback.

### Phase 4: Analyst Questions

- Add intent parser.
- Add simple query planner.
- Add deterministic pandas/SQL executor.
- Add cohort memory later.

### Phase 5: Builder + Export

- Add visual builder schema/render endpoints.
- Add filtered dashboard.
- Add PDF executive report.
- Add PPTX report.

## Practical Copy Strategy

Do not copy the whole old platform directly. It has many mature modules, but the current MVP has simpler naming and cleaner scope.

Best approach:

1. Copy concepts and schemas first.
2. Port one service at a time.
3. Keep route names compatible with the current app where possible.
4. Add tests after each feature.
5. Only add async jobs after dataset persistence works.

## First Functions I Would Port

1. `DatasetRecord` from `backend/core/dataset.py`
2. `save_dataset_record`, `load_dataset_record`, `list_persisted_dataset_ids` from `backend/core/dataset_registry.py`
3. `build_column_schema` from `backend/services/processing/schema_service.py`
4. `build_dataset_overview` from `backend/services/processing/overview_service.py`
5. `KpiCard`, `ChartSpec`, `DashboardView` from `backend/schemas/dashboard.py`
6. `generate_charts_from_schema` from `backend/services/analytics/chart_engine.py`
7. `compute_dashboard_kpis` from `backend/services/analytics/kpi_engine.py`
8. `generate_base_intelligence_brief` from `backend/services/analytics/insight_intelligence_service.py`

That sequence gives the app a stronger brain without forcing the full old architecture in one move.
