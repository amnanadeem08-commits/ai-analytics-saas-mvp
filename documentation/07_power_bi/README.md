# 07 — Power BI Mapping

| Data Bot AI capability | Power BI analogue | Notes |
|------------------------|-------------------|-------|
| Upload + profiling | Power Query / Data view | Local CSV/XLSX first |
| Data cleaning | Power Query transforms | Nulls/duplicates/outliers |
| Dashboard KPIs | Cards + measures | `kpi_service` / analytics dashboard |
| Charts | Report visuals | Plotly in Streamlit |
| Dashboard Studio | Report canvas | Visual builder routes |
| DAX Studio page | DAX measures | `/dax` routes + `dax_service` |
| SQL Lab | DirectQuery / SQL | `/sql-lab` |
| AI Insights / Analyst | Smart Narrative / Copilot-like | Different stack (LLM services) |
| Storyboard / PPT-PDF | Paginated / export | reportlab / python-pptx |
| Themes / branding | Theme JSON | `/themes`, `/branding` |
| Evaluation | Performance Analyzer (loose) | Quality metrics, not UI perf |
| RBAC / orgs | Workspace roles | Custom RBAC API |
| Monitoring | Admin monitoring | Health/metrics endpoints |
| Governance docs | Tenant governance | Security + DR guides |

## Example: KPI

Power BI: `Total Sales = SUM(Sales[Amount])`  
Data Bot AI: dashboard KPI cards derived from dataset analytics services after upload.
