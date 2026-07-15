# Accessibility Guide

## Contrast

- Primary navy `#174A7C` on white meets WCAG AA for large text; body text uses `#0F172A`.
- Status chips always include a text label (not color alone).
- Chart palette mixes cool/warm hues for colorblind differentiation; still prefer patterns/labels in dense charts.

## Interaction

- Primary actions use Streamlit buttons (keyboard focusable).
- Captions / `help=` provide secondary context for metrics and inputs.
- Destructive actions: use `danger_button` + caption reminder.

## Motion & density

- Prefer spacing tokens over crowding.
- Responsive: typography and steppers scale down under 700px width.

## Remaining debt

- Full automated contrast audit  
- Skip links / landmark roles beyond Streamlit defaults  
- Admin/ops page full migration to design-system chrome  

See Sprint 8.9 deliverables report for inventory.
