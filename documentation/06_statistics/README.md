# 06 — Statistics Handbook

Concepts commonly used by analytics platforms like Data Bot AI. Where the repo uses them is noted; otherwise labeled **general teaching**.

## Descriptive statistics

| Concept | Definition | Formula (simple) | Business meaning | Likely usage in Data Bot AI |
|---------|------------|------------------|------------------|-----------------------------|
| Mean | Average | Σx / n | Typical value | KPI totals/averages on dashboards |
| Median | 50th percentile | middle value | Robust center | Outlier-resistant summaries (**Not verified** exact median API) |
| Mode | Most frequent | argmax freq | Common category | Categorical profiling |
| Variance / Std Dev | Spread | Σ(x-μ)²/(n-1) ; √var | Volatility | Distribution charts |
| Percentiles / Quartiles | Ranked cut points | order stats | Segmentation | Profiling / charts |
| Correlation | Linear association | Pearson r | Co-movement | Charts / correlation views |
| Outliers | Extreme points | IQR/z-score heuristics | Data quality | Cleaning flows |

## Inferential / forecasting (teaching + project touchpoints)

| Topic | Teaching point | Project touchpoint |
|-------|----------------|--------------------|
| Regression | Predict continuous Y from X | Forecast/prediction services exist |
| Confidence intervals | Uncertainty of estimate | Explainability services (**depth Not verified**) |
| Hypothesis testing | Compare groups | **Not verified** as first-class product feature |
| Time series / trend | Order by time | Sample sales has `date`; forecast pipeline |
| Forecast error | MAE/RMSE/MAPE | Evaluation/scoring services |

## Interview questions (samples)

1. Mean vs median when outliers exist?
2. What does correlation not imply?
3. How would you detect outliers before KPI calculation?
4. Which error metric for forecasting revenue?

## Power BI / Python mapping

- Power BI: DAX `AVERAGE`, `MEDIAN`, `STDEV.P`, visuals
- Python: `pandas` describe/corr; used heavily in backend processing
