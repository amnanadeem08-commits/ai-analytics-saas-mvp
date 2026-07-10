# Data Bot AI Explained Like a Power BI Project

**Audience:** Power BI analysts, BI developers, business stakeholders  
**Product:** Data Bot AI v1.0.0  
**Goal:** Explain every important technical idea in **analytics language** — the way you already think about Power Query, models, measures, workspaces, and refresh pipelines.

> If you know Power BI, you already understand most of Data Bot AI.  
> The names are different. The **jobs** are familiar.

---

## 1. The big picture (one sentence)

**Data Bot AI is like a Power BI workspace that can also hire a team of AI analysts**, clean your Excel/CSV, build KPI cards, write an executive narrative, check its own work, and save the artifacts — all in one product.

| Power BI world | Data Bot AI world |
|----------------|-------------------|
| .pbix / workspace | Streamlit app + FastAPI backend |
| Power Query | Upload + data cleaning + profiling |
| Data model / tables | Dataset + metadata |
| Measures (DAX) | KPI detection + DAX Studio page |
| Report canvas | Dashboard + Dashboard Studio |
| Smart Narrative / Copilot-style help | AI Analyst + AI Insights |
| Workspace roles | Organizations + RBAC |
| Gateway / refresh | Jobs + workflow engine |
| SharePoint / OneDrive files | Object storage |
| Admin portal monitoring | Health + metrics pages |

---

## 2. Dataset upload → “Get Data”

**Technical name:** Upload / dataset service  

**Power BI language:**  
Exactly like **Get Data → Excel/CSV** in Power BI Desktop.

1. You pick a file  
2. The system loads rows and columns  
3. It stores a usable table for analysis  
4. You get a `dataset_id` (like a table name / model entity you keep using)

**Business meaning:** Without a clean table, no KPI, chart, or AI answer is trustworthy.

---

## 3. Data cleaning & profiling → Power Query + Data view

**Technical names:** data cleaning, profiling, schema detection  

**Power BI language:**  
This is your **Power Query** step plus the **Data view** inspection.

| What happens | Power BI analogue |
|--------------|-------------------|
| Fix nulls / duplicates / outliers | Transform / Replace / Remove duplicates |
| Detect numeric vs categorical columns | Column types in Power Query |
| Row/column counts, missingness | Column quality / profiling |
| Preview first rows | Data view preview |

**Why it matters:** Bad types and dirty nulls break measures the same way a wrong data type breaks DAX.

---

## 4. Dashboard & KPI cards → Report cards + measures

**Technical names:** analytics dashboard, KPI service  

**Power BI language:**  
Think of the **report canvas** with **Card** visuals driven by measures.

Instead of writing:

```dax
Total Sales = SUM(Sales[sales])
```

Data Bot AI builds KPI cards from the uploaded table (totals, trends, segment hints).

**Business meaning:** Leadership sees “what happened” before anyone opens a chart.

---

## 5. Charts & Dashboard Studio → Visuals + report canvas

**Technical names:** chart service, visual builder  

**Power BI language:**

- Charts page ≈ inserting Clustered column / Line / Scatter visuals  
- Dashboard Studio ≈ designing the **report canvas** (layout of visuals)  
- Themes / branding ≈ Power BI theme JSON + report branding

---

## 6. SQL Lab → DirectQuery / SQL endpoint thinking

**Technical name:** SQL Lab  

**Power BI language:**  
Like writing SQL against your model/source when DirectQuery or a SQL endpoint is available — exploratory queries on the loaded dataset.

---

## 7. DAX Studio (in the product) → Measures playground

**Technical name:** DAX Studio / `dax_service`  

**Power BI language:**  
Exactly the comfort zone of a BI developer: **measure logic**, business calculations, Power BI–style thinking — but inside Data Bot AI’s lab page.

---

## 8. AI Analyst → “A team of Power BI analysts in one chat”

**Technical names:** AI Analyst, planning engine, multi-agent framework, tools  

**Power BI language:**  
Do **not** think “mysterious AI black box.”  
Think: **multiple Power BI analysts working together on the same workbook.**

| Analyst role | What they do (analytics language) |
|--------------|-----------------------------------|
| Analyst A | Cleans / prepares the data (Power Query mindset) |
| Analyst B | Finds KPIs and important metrics (measure mindset) |
| Analyst C | Validates results (peer review / QA of numbers) |
| Analyst D | Writes the executive summary (Smart Narrative mindset) |

**Planning engine** = the team lead who decides *who speaks next* and *in what order* — like a senior analyst assigning tasks before the board meeting.

**Tool selection** = choosing the right visual or calculation method — “Should we use a card, a trend, a segment breakdown, or a document lookup?”

---

## 9. Workflow engine → Refresh pipeline / ETL stages

**Technical name:** Workflow engine  

**Power BI language:**  
Comparable to a **Power BI refresh pipeline** or an **ETL pipeline**:

1. Stage 1 runs (e.g. prepare data)  
2. Output becomes input for Stage 2 (e.g. compute KPIs)  
3. Stage 3 validates  
4. Stage 4 produces narrative / artifacts  

Each stage runs in sequence and passes its output to the next stage — same mental model as **Power Query steps** or an **Azure Data Factory / deployment pipeline** chain.

**UI:** Workflow Monitor ≈ watching refresh history / pipeline runs.

---

## 10. RAG (Retrieval-Augmented Generation) → “Don’t answer from memory only”

**Technical name:** RAG / knowledge retrieval / embeddings / vector search  

**Power BI language:**  
Think of RAG as **searching your organization’s documents before answering a question**, similar to how a Power BI report can **reference multiple datasets / shared tables** instead of relying only on what one person remembers.

| Without RAG | With RAG |
|-------------|----------|
| Answer from “model memory” only (risky) | First look up relevant notes/docs/knowledge, then answer |
| Like guessing a KPI definition | Like checking the certified dataset + glossary |

**Knowledge Center** ≈ a library of business documents you ingest so answers stay grounded.

> Note: A `/rag` route file exists in the repo; whether it is mounted in the live app factory is labeled **Not verified** in the engineering handbook. Knowledge + RAG **services** exist and are part of the AI stack.

---

## 11. Memory → Report context / session continuity

**Technical name:** Memory service  

**Power BI language:**  
Like **report filters + conversation context** that stay with you during a session — the analyst remembers what dataset and question you were working on, instead of starting from a blank page every time.

**Session History** ≈ reopening a previous analysis meeting.

---

## 12. Evaluation & validation → Peer review + Performance Analyzer (quality, not only speed)

**Technical names:** evaluation framework, AI validation, output validation  

**Power BI language:**

- **Evaluation** ≈ a QA checklist after the report is built: “Are insights strong? Weak? Missing evidence?”  
- **Validation** ≈ “Does this number / claim pass business-safe checks?” before you present to leadership  

Loose analogue to **Performance Analyzer** (inspect quality of the run) — here the focus is **answer quality**, not only visual render speed.

---

## 13. Jobs & workers → Scheduled refresh / background refresh

**Technical names:** job service, queue, workers  

**Power BI language:**  
Like **scheduled refresh** or a long refresh that runs in the background while you keep working.

| Job idea | Power BI analogue |
|----------|-------------------|
| Submit job | Start refresh |
| Progress / status | Refresh history |
| Retry | Re-run failed refresh |
| Inline vs async | Refresh now vs schedule |

**Job Monitor** page ≈ Refresh history pane.

---

## 14. Object storage → SharePoint / OneDrive for report artifacts

**Technical name:** Storage service (local provider; S3 stub for later)  

**Power BI language:**  
Where **files and versions** live — datasets, exports, artifacts — similar to keeping `.pbix` / exported PDFs / source files in SharePoint with version history.

| Storage idea | Power BI analogue |
|--------------|-------------------|
| Upload artifact | Upload file to library |
| Versions / rollback | Version history |
| Archive | Soft-retire a file |
| Streaming download | Download large export |

---

## 15. Organizations, workspaces, RBAC → Tenant / workspace roles

**Technical names:** organizations, workspaces, RBAC  

**Power BI language:**  
This is your **Power BI tenant + workspace roles** model.

| Data Bot AI | Power BI |
|-------------|----------|
| Organization | Tenant / capacity boundary (simplified) |
| Workspace | Workspace |
| Roles & permissions | Admin / Member / Contributor / Viewer-style access |
| Invitations | Add user to workspace |

**Business meaning:** Not everyone should edit measures or see admin billing.

---

## 16. Authentication (JWT login) → Organizational sign-in

**Technical name:** Auth / JWT  

**Power BI language:**  
Like signing into the Power BI service before you can open a workspace.  
You get a session token (access) and can refresh it — similar to staying signed in securely.

Brute-force lockout ≈ account protection after too many wrong passwords.

---

## 17. Billing, usage, API keys → Capacity / premium thinking (MVP)

**Technical names:** subscription plans, usage, API keys, admin  

**Power BI language:**  
Closest mental model: **capacity / license limits** and **service principals / access keys** for automation.

| Feature | Analytics language |
|---------|-------------------|
| Free / Pro / Enterprise plans | SKU / license tier |
| Usage quotas | Capacity limits |
| API keys | Service access for systems (not interactive user) |
| Invoices / credits | Commercial tracking (**no live payment gateway in v1.0**) |

---

## 18. Monitoring & health → Admin portal / service health

**Technical names:** monitoring, metrics, liveness/readiness  

**Power BI language:**  
Like checking **service health** and admin monitoring:

- Is the service alive?  
- Are dependencies (database, storage, queue) ready?  
- Are error rates / timings healthy?

---

## 19. Reports, storyboard, exports → Paginated / PowerPoint pack for leadership

**Technical names:** PDF/PPT export, storyboard engine  

**Power BI language:**  
Building the **board pack**:

- PDF / PPT ≈ export for email / meeting  
- Storyboard ≈ narrative slide flow (title → KPIs → insight → action)  
- Location insights ≈ map / region breakdown thinking

---

## 20. Forecast & prediction modules → “What happens next?” analytics

**Technical names:** forecast pipeline, prediction engine, scenarios  

**Power BI language:**  
Like adding a **forecast line** on a chart or running a what-if for next period — with extra governance/explainability modules in the codebase.

Treat accuracy claims carefully: architecture exists; business accuracy is **use-case dependent** (**Not verified** as a guaranteed forecast product SLA).

---

## 21. Security hardening → Tenant security settings

**Technical names:** security headers, CORS, rate limit, CSRF, secrets validation  

**Power BI language:**  
Tenant/admin security controls:

- Who can call the service (CORS ≈ allowed domains)  
- Stop abuse (rate limit ≈ throttling)  
- Protect browser sessions (CSRF)  
- Don’t ship with default passwords/secrets (like not publishing with “Password123”)

---

## 22. End-to-end story (Power BI style)

```text
Get Data (Upload CSV)
    → Power Query (Clean + Profile)
    → Model / Dataset ready
    → Build visuals + KPI cards
    → Optional: SQL / DAX labs
    → Ask the analyst team (AI Analyst)
         Analyst A clean → B KPIs → C validate → D executive summary
    → If needed, search company docs first (RAG / Knowledge)
    → Run as a pipeline (Workflow) or background refresh (Jobs)
    → Save files/versions (Storage)
    → Share only to allowed roles (Org + RBAC)
    → Export board pack (PDF/PPT / Storyboard)
    → Admin checks health (Monitoring)
```

That is Data Bot AI — **explained like a Power BI project**.

---

## 23. Quick glossary (tech word → analytics word)

| If engineers say… | Say this instead… |
|-------------------|-------------------|
| Multi-agent planning | Multiple Power BI analysts collaborating with a team lead |
| Tool selection | Choosing the right visual / calculation / lookup method |
| RAG | Search org documents before answering |
| Embeddings / vector search | Smart document search index |
| Workflow engine | Refresh / ETL pipeline stages |
| Job queue / worker | Background / scheduled refresh |
| Evaluation | QA scorecard for insights |
| Validation | Peer review before publishing |
| Repository / ORM | Where certified tables are stored |
| Object storage | File library with version history |
| RBAC | Workspace roles |
| JWT | Secure sign-in session |
| Middleware | Gateway security checks before the report service runs |
| Circuit breaker / retry | Refresh retry + fail-safe when a source is down |
| Streamlit UI | The interactive report/app experience |
| FastAPI | The service layer behind the report |

---

## 24. What this document is / is not

- **Is:** A translation layer for Power BI minds reading Data Bot AI v1.0  
- **Is not:** A claim that Data Bot AI is Power BI, or that every Power BI feature exists here  
- Gaps and MVP limits remain in `KNOWN_ISSUES.md` (no live billing gateway, some in-memory stores, etc.)

---

## Related handbook pages

- [07 Power BI Mapping (table)](../07_power_bi/README.md)  
- [08 AI Handbook](../08_ai/README.md)  
- [05 Data Science Handbook](../05_data_science/README.md)  
- [01 Executive Summary](../01_executive_summary/README.md)  
