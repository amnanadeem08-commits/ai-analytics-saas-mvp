# Layout Guide

Spacing tokens (`frontend/design_system/spacing.py`):

| Token | Value |
|-------|-------|
| xxs | 0.25rem |
| xs | 0.5rem |
| sm | 0.75rem |
| md | 1rem |
| lg | 1.5rem |
| xl | 2rem |
| xxl | 3rem |
| section | 1.25rem |

Radius: sm 6px · md 10px · lg 14px · pill.

**Patterns**

- Page: `page_header(title, caption)` then content sections with `section_header`.
- Prefer `st.columns` + design-system spacing over ad-hoc pixel padding.
- Cards use `.ds-card` / `.ds-kpi` with consistent border and radius.
- Workflow path uses `workflow_stepper` (Upload → … → Export).

Sidebar / top navigation remain Streamlit-native; captions and Connection expander follow Sprint 8.8 IA.
