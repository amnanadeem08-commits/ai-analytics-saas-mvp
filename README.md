# AI Analytics SaaS MVP

A local-first AI Analytics SaaS MVP built with:

- Backend: FastAPI
- Frontend: Streamlit
- Data processing: Pandas
- Storage: Local CSV + JSON metadata
- AI layer: Rule-based insights + LLM-ready placeholder

This MVP is intentionally simple and modular. It supports CSV upload, validation, preview, summary statistics, basic dashboards, AI-style insights, and natural language questions over uploaded datasets.

---

## Project Structure

```text
ai-analytics-saas/
├── backend/
│   ├── main.py
│   ├── api/routes/
│   ├── core/
│   ├── models/
│   ├── services/
│   ├── processing/
│   ├── ai/
│   ├── storage/
│   └── utils/
├── frontend/
│   ├── streamlit_app.py
│   ├── api_client/
│   └── components/
├── data/
│   ├── uploads/
│   ├── processed/
│   ├── metadata/
│   └── samples/
├── scripts/
└── tests/
```

---

## Phase 1: Run FastAPI Backend

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
GET /health
```

Upload dataset:

```text
POST /upload
```

Summary endpoint:

```text
GET /analytics/{dataset_id}/summary
```

---

## Phase 2: Run Streamlit Frontend

Keep the FastAPI backend running in one terminal.

Open a second terminal:

```bash
# Activate the same environment first
streamlit run frontend/streamlit_app.py
```

Frontend URL is usually:

```text
http://localhost:8501
```

Use the sample dataset:

```text
data/samples/sample_sales_data.csv
```

---

## Phase 3: AI Insights + Questions

Backend endpoints:

```text
GET /insights/{dataset_id}
POST /insights/{dataset_id}/ask
```

Example questions:

```text
How many rows are in this dataset?
Which product has the highest sales?
What is the average profit?
Are there missing values?
Show total sales by region.
```

---

## Notes

- This MVP uses local storage only.
- PostgreSQL, authentication, workspaces, billing, and background jobs are intentionally left for the scalable SaaS phase.
- The LLM engine is a placeholder so you can later connect OpenAI, Azure OpenAI, or another provider without changing the rest of the architecture.
