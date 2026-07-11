# Chart Guide

Module: `frontend/design_system/charts.py`.

## Palette (accessible, light-background)

1. `#174A7C` primary navy  
2. `#B88322` accent gold  
3. `#15803D` green  
4. `#B91C1C` red  
5. `#0369A1` info blue  
6. `#7C3AED` violet (categorical)  
7. `#0F766E` teal  
8. `#C2410C` orange  

## Layout defaults

- Horizontal legend above the plot  
- Plot background `#F5F7FA`, paper `#FFFFFF`  
- Margins ~48/24/56/48  
- Gridlines use border color; no heavy zerolines  
- Fonts from typography stack  

## Usage

```python
from frontend.design_system.charts import apply_chart_layout, render_chart

apply_chart_layout(fig, title="Revenue by segment")
# or
render_chart(fig, title="Revenue by segment")
```

`frontend/components/chart_components.py` applies `apply_chart_layout` in `_prepare_figure`.
