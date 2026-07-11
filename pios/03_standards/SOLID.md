# SOLID Principles (project application)

- **S** — One service owns one domain concern (cleaning, billing, RAG, etc.)
- **O** — Extend via registries/plugins (`DomainRegistry`, KPI/viz/metric registries) rather than editing every consumer
- **L** — Storage/queue/repo implementations remain substitutable behind interfaces where present
- **I** — Prefer narrow service APIs over god-objects
- **D** — Routes depend on services; services depend on abstractions (repos/storage), not Streamlit or HTTP details
