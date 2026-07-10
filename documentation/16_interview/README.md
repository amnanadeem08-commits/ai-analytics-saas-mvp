# 16 — Interview Preparation

## Project discussion (STAR-ready)

**Situation:** Need a local-first AI analytics SaaS MVP.  
**Task:** Deliver upload→insights→AI analyst→platform ops through v1.0.  
**Action:** Layered FastAPI/Streamlit architecture with tests and hardening.  
**Result:** Tagged `v1.0.0` with 634 passing tests and documented limitations.

## Sample Q&A

### System design
**Q:** How is multi-tenancy handled?  
**A:** Organizations and workspaces with RBAC evaluation (`rbac_service.evaluate_access` / `has_permission`).

### FastAPI
**Q:** Where is middleware configured?  
**A:** `backend/main.py` — CORS, GZip, security headers, rate limit, CSRF, monitoring, auth context.

### Security
**Q:** How are passwords stored?  
**A:** PBKDF2-HMAC-SHA256 with salt (`password_service`), not plaintext.

### AI
**Q:** How do you reduce hallucinations?  
**A:** Retrieval (RAG/knowledge), tool-grounded workflows, and validation/evaluation services — not a hard guarantee.

### Data
**Q:** Walk through upload.  
**A:** `/upload` → upload/dataset services → metadata + processed artifacts → analytics endpoints.

### Behavioral
**Q:** A limitation you shipped?  
**A:** In-memory commercial stores and no payment gateway — documented in KNOWN_ISSUES, scheduled on ROADMAP.

More prompts: Python GIL vs workers, idempotent jobs, circuit breakers, pagination, CORS credentials vs `*`, Alembic vs create_all.
