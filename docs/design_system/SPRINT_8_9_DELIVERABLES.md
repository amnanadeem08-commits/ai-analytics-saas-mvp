# Sprint 8.9 — Product Design System Deliverables

**Branch:** `develop`  
**Scope:** Frontend only  
**Date:** 2026-07-11  
**Product:** Khaldun AI DataBot

## Before vs After

| Before | After |
|--------|-------|
| Ad-hoc colors/padding in pages + `ux_states` CSS | Central tokens in `frontend/design_system/` |
| Chart margins/legends varied per figure | `apply_chart_layout` + shared palette |
| Metric/section headers duplicated | `layout` + `cards` primitives |
| Status colors hardcoded in UX kit | `STATUS_COLORS` + badge helpers |
| No formal DS docs | `docs/design_system/*` guides |

## Component inventory

See [COMPONENT_GUIDE.md](./COMPONENT_GUIDE.md). Modules created:

`colors`, `typography`, `spacing`, `icons`, `theme`, `tokens`, `charts`, `tables`, `forms`, `buttons`, `cards`, `alerts`, `modals`, `layout`, `navigation`.

## Design token reference

```python
from frontend.design_system import token_reference
token_reference()  # colors, spacing, radius, typography, chart_palette
```

Canonical dumps: [COLOR_GUIDE](./COLOR_GUIDE.md), [TYPOGRAPHY_GUIDE](./TYPOGRAPHY_GUIDE.md), [LAYOUT_GUIDE](./LAYOUT_GUIDE.md).

## Screenshots

Streamlit screenshots not automated. Capture manually:

1. Home with DS section headers + stepper  
2. Dashboard charts with DS layout  
3. Evaluation scorecards via `metric_cards`  
4. Status chips on Job/Workflow monitors  

Store under `documentation/12_pictorial_evidence/`.

## Migration summary

1. Added `frontend/design_system/` package.  
2. `streamlit_app.main()` calls `apply_design_system()` + `ensure_session_palette()`.  
3. `ux_states` delegates to DS tokens (backward compatible).  
4. Migrated: `metric_cards`, `chart_components._prepare_figure`, Home quick actions, Evaluation scorecards.  
5. Docs under `docs/design_system/`.

## Pages updated

- Shell: `frontend/streamlit_app.py`  
- Home, Evaluation Dashboard  
- Shared: `ux_states`, `metric_cards`, `chart_components`  
- Indirect: all pages using UX kit inherit DS CSS variables  

## Remaining inconsistencies

- Billing / admin / ops pages still use local headers in places  
- Some legacy HTML CSS in AI Insights / Home hero not fully tokenized  
- Plotly charts outside `chart_components` may still use ad-hoc layout  
- Fluent-like density pass for forms on Auth pages deferred  

## Stop

Sprint 8.9 complete. Do not start the next sprint in this task.
