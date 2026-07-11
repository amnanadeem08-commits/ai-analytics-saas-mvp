# Component Guide

Package: `frontend/design_system/`.

| Component | Module | API |
|-----------|--------|-----|
| Primary / Secondary / Danger / Success buttons | `buttons.py` | `primary_button`, `secondary_button`, `danger_button`, `success_button` |
| Section / KPI / Metric cards | `cards.py` | `section_card`, `kpi_card`, `metric_cards` |
| Alerts / notifications | `alerts.py` | `alert`, `notify_*` |
| Badges / tags / status chips | `alerts.py` | `render_badge`, `tag`, `status_chip` |
| Forms / search / progress | `forms.py` | `search_box`, `progress_indicator`, `labeled_*` |
| Tables | `tables.py` | `data_table` |
| Charts | `charts.py` | `apply_chart_layout`, `render_chart`, `chart_palette` |
| Dialogs | `modals.py` | `confirm_dialog`, `details_modal` |
| Layout | `layout.py` | `page_header`, `section_header`, `spacer` |
| Tabs / accordion / stepper | `navigation.py` | `tabs`, `accordion`, `workflow_stepper` |
| Icons | `icons.py` | `icon(name)` |

Sprint 8.8 `frontend/components/ux_states.py` now delegates badges, steppers, and section headers to these tokens so existing pages stay compatible.
