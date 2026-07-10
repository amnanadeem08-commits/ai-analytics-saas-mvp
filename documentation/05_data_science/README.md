# 05 — Data Science Handbook

This chapter explains Data Bot AI from a data-science lens using **verified** product surfaces.

## Data Cleaning

- **Why:** Raw CSV/Excel contains nulls, duplicates, type noise
- **Where:** `data_cleaning_service`, processing `data_cleaner`, UI Data Cleaning
- **Business value:** Trustworthy KPIs and charts
- **Limitation:** Pandas `object` dtype warnings documented in KI-008

## EDA / Profiling / Schema

- Overview endpoints on datasets: row/column counts, column groups (numeric/categorical), missingness, preview
- Services: `overview_service`, `data_profiler`, `schema_service`, `column_detector`

## KPI Detection & Business Metrics

- `kpi_service`, dashboard KPI cards with sparklines, reasons, recommended actions (verified in dataset phase tests historically)
- Domain intelligence: `domain_intelligence_service`, registries under `backend/registry/`

## Executive Insights & Storytelling

- Insight services, executive reasoning, storyboard engine, PDF/PPT export services
- UI: AI Insights, Storyboard, Reports

## Forecast Architecture

Verified forecast-related services exist:

- adapter, capability, dataset, explainability, governance, pipeline, plugin, scenario
- Prediction engine + prediction validation

Treat forecast depth as **modular MVP architecture**; production model accuracy claims: **Not verified**.

## Validation & Evaluation

- AI validation, output validation, evaluation metrics across workflow/agents/tools/RAG/LLM
- Business value: reduce hallucinations and measure quality

## Decision Intelligence & Memory

- `decision_intelligence_service`, `memory_service`
- Supports analyst continuity across sessions

## Knowledge Retrieval / Business AI

- Knowledge ingestion + RAG stack services
- LLM providers: OpenAI, Anthropic, local stubs/adapters under `providers/`

## Practical scenario

Sales CSV (`data/samples/sample_sales_data.csv`) → upload → overview → dashboard KPIs (sales/profit) → AI Analyst question → optional evaluation score.
