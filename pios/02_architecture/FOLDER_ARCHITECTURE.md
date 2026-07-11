# Folder Architecture

```text
ai-analytics-saas-mvp/
├── backend/          # FastAPI application
│   ├── api/routes/   # HTTP route modules
│   ├── services/     # Domain services (~89 *_service.py)
│   ├── models/       # Pydantic / domain models
│   ├── repositories/ # memory + SQLAlchemy
│   ├── storage/      # Object storage providers
│   ├── rag/          # RAG package
│   ├── ai/           # AI runtime helpers
│   ├── registry/     # Domain/KPI/viz/metric registries
│   ├── jobs|queue|workers/
│   ├── monitoring|logging|security|reliability|performance/
│   └── core|config|database/
├── frontend/         # Streamlit UI
│   ├── streamlit_app.py
│   ├── app_pages/
│   ├── api/ + api_client/
│   └── utils|components|services/
├── tests/            # pytest suite (125 test_*.py files at v1.0)
├── docs/             # ADR + release guides
├── documentation/    # Engineering handbook
├── release/          # v1.0 / v1.0-rc checklists
├── pios/             # THIS operating system (control plane)
├── docker/ deploy/ alembic/ data/ scripts/
└── requirements*.txt
```

Deep reference: [`documentation/03_folders/README.md`](../../documentation/03_folders/README.md), [`documentation/02_architecture/README.md`](../../documentation/02_architecture/README.md)
