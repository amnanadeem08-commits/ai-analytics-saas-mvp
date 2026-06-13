from __future__ import annotations

import re
from typing import Any

import pandas as pd

from backend.processing.column_detector import detect_column_types
from backend.services.dataset_service import load_dataset_dataframe
from backend.services.domain_intelligence_service import detect_domain


def _metric(df: pd.DataFrame, prompt: str) -> str | None:
    numeric = detect_column_types(df)["numeric_columns"]
    for column in numeric:
        if column.lower().replace("_", " ") in prompt.lower():
            return column
    for hint in ["revenue", "sales", "amount", "profit", "cost", "churn"]:
        for column in numeric:
            if hint in column.lower():
                return column
    return numeric[0] if numeric else None


def _table() -> str:
    return "Dataset"


def _data_understanding(df: pd.DataFrame) -> dict[str, Any]:
    column_types = detect_column_types(df)
    return {
        "field_types": {
            "numeric": column_types["numeric_columns"],
            "categorical": column_types["categorical_columns"],
            "date_time": column_types["date_columns"],
            "text": [
                column
                for column in df.columns
                if column
                not in set(
                    column_types["numeric_columns"]
                    + column_types["categorical_columns"]
                    + column_types["date_columns"]
                    + column_types["boolean_columns"]
                )
            ],
            "boolean": column_types["boolean_columns"],
        },
        "supports": {
            "time_intelligence": bool(column_types["date_columns"]),
            "aggregation": bool(column_types["numeric_columns"]),
            "segmentation": bool(column_types["categorical_columns"] or column_types["boolean_columns"]),
            "comparison": bool(column_types["categorical_columns"] or column_types["boolean_columns"]),
        },
    }


def _analysis_type(prompt: str, dax: str = "") -> str:
    text = f"{prompt} {dax}".lower()
    if any(term in text for term in ["ytd", "mtd", "qtd", "mom", "yoy", "rolling", "trend", "over time"]):
        return "Trend Analysis"
    if any(term in text for term in ["why", "driver", "cause", "root"]):
        return "Root Cause Analysis"
    if any(term in text for term in ["by ", "top", "bottom", "compare", "versus", "segment"]):
        return "Comparison Analysis"
    if any(term in text for term in ["distribution", "spread", "range"]):
        return "Distribution Analysis"
    if any(term in text for term in ["group", "cohort", "cluster"]):
        return "Segmentation Analysis"
    return "KPI Tracking"


def _logic_validation(df: pd.DataFrame, prompt: str, metric: str | None, analysis_type: str) -> dict[str, Any]:
    understanding = _data_understanding(df)
    supports = understanding["supports"]
    q = prompt.lower()
    invalid_reasons: list[str] = []
    warnings: list[str] = []
    dax_allowed = True

    if "no dax required" in q:
        invalid_reasons.append("The current analysis was already classified as structural, so DAX should not be forced.")
        dax_allowed = False
    if analysis_type == "Trend Analysis" and not supports["time_intelligence"]:
        invalid_reasons.append("Time intelligence was requested, but no date/time field was detected.")
        dax_allowed = False
    if any(term in q for term in ["sum", "total", "revenue", "sales", "amount", "profit", "ytd", "rolling"]) and not metric:
        invalid_reasons.append("A measurable numeric field is required for this aggregation, but none was detected.")
        dax_allowed = False
    if analysis_type in {"Segmentation Analysis", "Comparison Analysis", "Root Cause Analysis"} and not supports["segmentation"]:
        warnings.append("No categorical grouping field was detected, so segment comparison will be limited.")
    if analysis_type == "Distribution Analysis":
        dax_allowed = False
        warnings.append("Distribution analysis is usually visual/structural; a DAX measure is not required.")

    should_not_do = []
    if not supports["time_intelligence"]:
        should_not_do.append("Do not apply YTD, MoM, YoY, rolling-period, or Date-table logic without a valid date field.")
    if not metric:
        should_not_do.append("Do not apply SUM or AVG to text-only fields.")
    if not supports["aggregation"]:
        should_not_do.append("Do not force KPI tracking when no numeric KPI exists.")

    return {
        "is_valid": not invalid_reasons,
        "dax_allowed": dax_allowed and not invalid_reasons,
        "field_used": metric or "No numeric measure selected",
        "field_type": "numeric" if metric else "none",
        "validation_summary": (
            "Analysis logic is valid for the detected dataset structure."
            if not invalid_reasons
            else "Analysis logic was corrected because the requested method does not match the dataset structure."
        ),
        "invalid_reasons": invalid_reasons,
        "warnings": warnings,
        "should_not_do": should_not_do,
        **understanding,
    }


def _measure_name(dax: str) -> str:
    first_line = dax.strip().splitlines()[0] if dax.strip() else "Generated Measure"
    return first_line.split("=", 1)[0].strip() or "Generated Measure"


def _recommended_visuals(dax: str, domain: str, analysis_type: str = "KPI Tracking") -> list[str]:
    if analysis_type == "Trend Analysis":
        return ["Line Chart"]
    if analysis_type == "Comparison Analysis":
        return ["Bar Chart"]
    if analysis_type == "Segmentation Analysis":
        return ["Stacked Bar Chart"]
    if analysis_type == "Root Cause Analysis":
        return ["Decomposition Tree"]
    if analysis_type == "Distribution Analysis":
        return ["Histogram"]
    text = dax.lower()
    visuals = ["KPI Card", "Matrix/Table"]
    if "totalytd" in text or "datesinperiod" in text or "rolling" in text:
        visuals.extend(["Line Chart", "Area Chart", "Combo Chart"])
    elif "rate" in text or "divide" in text:
        visuals.extend(["KPI Card", "Trend Line", "Segment Bar Chart"])
    elif "sum(" in text:
        visuals.extend(["Bar Chart", "Line Chart", "Regional Map"])
    if domain in {"Customer Churn", "Healthcare"}:
        visuals.append("Risk Segment Heatmap")
    return list(dict.fromkeys(visuals))


def _measure_preview(dax: str, metric: str | None, domain: str) -> dict[str, Any]:
    name = _measure_name(dax)
    text = dax.lower()
    if "rate" in text or "divide" in text:
        value_type = "percentage"
        expected_format = "0.00%"
    elif "average" in text or "avg" in text:
        value_type = "average"
        expected_format = "#,##0.00"
    elif "countrows" in text:
        value_type = "count"
        expected_format = "#,##0"
    else:
        value_type = "numeric total"
        expected_format = "#,##0.00"
    return {
        "measure_name": name,
        "metric": metric or "records",
        "domain": domain,
        "value_type": value_type,
        "expected_format": expected_format,
        "preview_note": (
            f"{name} should be validated in Power BI against the uploaded dataset table and filtered by the report context."
        ),
    }


def _dashboard_guidance(dax: str, domain: str, analysis_type: str = "KPI Tracking") -> list[str]:
    name = _measure_name(dax)
    guidance = [f"Place {name} in the executive KPI row as a primary scorecard measure."]
    if analysis_type == "Trend Analysis" or "totalytd" in dax.lower() or "datesinperiod" in dax.lower():
        guidance.append("Add the measure to a monthly trend section with Date hierarchy drill-down.")
    if "rate" in dax.lower() or "divide" in dax.lower():
        guidance.append("Pair the measure with segment filters and a variance indicator against prior period.")
    if domain in {"Sales", "Customer Churn", "Healthcare"}:
        guidance.append(f"Use domain filters so executives can compare {domain.lower()} performance by segment and region.")
    return guidance


def _business_interpretation(dax: str, domain: str, metric: str | None) -> str:
    name = _measure_name(dax)
    if "churn" in dax.lower():
        return f"{name} quantifies customer loss pressure and should be used in retention reviews, PDF summaries, and board risk slides."
    if "rate" in dax.lower() or "divide" in dax.lower():
        return f"{name} converts raw activity into an executive-ready rate, making performance comparable across segments and time periods."
    if "totalytd" in dax.lower():
        return f"{name} shows year-to-date progress and is suitable for revenue, budget, and operating performance presentations."
    if "datesinperiod" in dax.lower():
        return f"{name} smooths recent performance into a rolling trend for investor, board, and management updates."
    return f"{name} summarizes {metric or 'business activity'} as a decision metric for dashboard, PDF, and PowerPoint reporting."


def _executive_summary(dax: str, domain: str, metric: str | None) -> str:
    name = _measure_name(dax)
    return (
        f"{name} is a Power BI-ready measure for {domain.lower()} analysis. "
        f"It should be used to monitor {metric or 'core performance'} and connect dashboard visuals to executive decisions."
    )


def _best_visual(dax: str, domain: str, analysis_type: str = "KPI Tracking") -> str:
    visuals = _recommended_visuals(dax, domain, analysis_type)
    return visuals[0]


def _refined_business_question(prompt: str, dax: str, domain: str, metric: str | None) -> str:
    if prompt.strip():
        base = prompt.strip()
    else:
        base = f"How should leadership monitor {metric or _measure_name(dax)}?"
    if "?" not in base:
        base = base.rstrip(".") + "?"
    return f"{base} Refined for {domain.lower()} reporting as an executive-ready Power BI measure."


def _dashboard_placement(dax: str, domain: str, analysis_type: str = "KPI Tracking") -> dict[str, str]:
    visual = _best_visual(dax, domain, analysis_type)
    if visual == "Line Chart":
        return {
            "page": "Executive Trends",
            "section": "Performance Over Time",
            "purpose_in_flow": "Show whether the business is improving, declining, or flattening over the reporting period.",
        }
    if "rate" in dax.lower() or "divide" in dax.lower():
        return {
            "page": "Executive Overview",
            "section": "Risk and Performance KPIs",
            "purpose_in_flow": "Give leadership an immediate read on risk, conversion, or efficiency before drilling into segments.",
        }
    return {
        "page": "Executive Overview",
        "section": "Primary KPI Scorecard",
        "purpose_in_flow": "Anchor the dashboard with the core business outcome before supporting charts explain the drivers.",
    }


def _next_best_question(dax: str, domain: str, metric: str | None) -> str:
    if "churn" in dax.lower():
        return "Which customer segment contributes the largest share of churn, and what retention action would reduce it fastest?"
    if "totalytd" in dax.lower() or "datesinperiod" in dax.lower():
        return f"Which region, product, or customer segment is driving the change in {metric or 'this measure'} over time?"
    if domain == "Healthcare":
        return "Which population segment has the highest risk level, and which indicator explains the concentration?"
    return f"What segment is driving the highest and lowest {metric or 'measure'} performance, and what action should management take?"


def _phase_outputs(
    dax: str,
    domain: str,
    metric: str | None,
    prompt: str,
    analysis_type: str,
    validation: dict[str, Any],
) -> dict[str, Any]:
    business_question = _refined_business_question(prompt, dax, domain, metric)
    dax_output = dax if validation.get("dax_allowed", True) else "No DAX required for this analysis"
    visual = _best_visual(dax, domain, analysis_type)
    placement = _dashboard_placement(dax, domain, analysis_type)
    meaning = _business_interpretation(dax, domain, metric)
    insight = _executive_summary(dax, domain, metric)
    return {
        "phase_1_intent": {
            "refined_business_question": business_question,
            "user_intent_summary": f"User wants {analysis_type.lower()} using {metric or 'available dataset fields'}.",
            "expected_outcome": "A validated BI-ready analysis plan that can be used in dashboard, report, or export output.",
        },
        "phase_2_validation": {
            "data_type_analysis": validation.get("field_types", {}),
            "valid_logic_check": "Valid" if validation.get("is_valid") else "Invalid - corrected before output",
            "required_fixes": validation.get("invalid_reasons", []) + validation.get("warnings", []),
            "recommended_analysis_type": analysis_type,
        },
        "phase_3_design": {
            "selected_analysis_type": analysis_type,
            "reason_for_selection": validation.get("validation_summary", ""),
            "data_strategy": (
                f"Use {metric} as the measurable field and match visuals/DAX to detected field types."
                if metric else "Use structural analysis because no valid numeric measure is available."
            ),
        },
        "phase_4_dax": {
            "dax_measures": dax_output,
            "short_explanation": explain_dax(dax) if validation.get("dax_allowed", True) else "No DAX required for this analysis.",
        },
        "phase_5_visual": {
            "best_visual_type": visual,
            "why_this_visual_fits": f"{visual} best matches {analysis_type.lower()} and the detected dataset structure.",
        },
        "phase_6_interpretation": {
            "business_interpretation": meaning,
            "key_insight": insight,
        },
        "phase_7_decision": {
            "key_decision_insight": insight,
            "next_best_analysis_step": _next_best_question(dax, domain, metric),
        },
        "phase_8_export": {
            "executive_summary": insight,
            "slide_ready_insight_points": [
                business_question,
                validation.get("validation_summary", ""),
                f"Recommended visual: {visual}",
                meaning,
                _next_best_question(dax, domain, metric),
            ],
        },
    }


def package_dax_measure(
    dax: str,
    domain: str,
    metric: str | None,
    analysis_type: str = "KPI Tracking",
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = validation or {}
    best_visual = _best_visual(dax, domain, analysis_type)
    placement = _dashboard_placement(dax, domain, analysis_type)
    dax_output = dax if validation.get("dax_allowed", True) else "No DAX required - analysis is structural."
    phases = _phase_outputs(dax, domain, metric, "", analysis_type, validation)
    return {
        **phases,
        "measure_preview": _measure_preview(dax, metric, domain),
        "analysis_type": analysis_type,
        "data_logic_validation": validation,
        "recommended_visual_types": _recommended_visuals(dax, domain, analysis_type),
        "best_visual": best_visual,
        "dashboard_integration_guidance": _dashboard_guidance(dax, domain),
        "dashboard_placement": placement,
        "pdf_ppt_business_interpretation": _business_interpretation(dax, domain, metric),
        "executive_insight_summary": _executive_summary(dax, domain, metric),
        "business_question_refined": _refined_business_question("", dax, domain, metric),
        "business_meaning": _business_interpretation(dax, domain, metric),
        "key_insight": _executive_summary(dax, domain, metric),
        "next_best_question": _next_best_question(dax, domain, metric),
        "export_ready_summary": _executive_summary(dax, domain, metric),
        "dax_output": dax_output,
    }


def _package_with_prompt(
    dax: str,
    domain: str,
    metric: str | None,
    prompt: str,
    analysis_type: str = "KPI Tracking",
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    package = package_dax_measure(dax, domain, metric, analysis_type, validation)
    package["business_question_refined"] = _refined_business_question(prompt, dax, domain, metric)
    package.update(_phase_outputs(dax, domain, metric, prompt, analysis_type, validation or {}))
    return package


def generate_dax(dataset_id: str, prompt: str) -> dict[str, Any]:
    df = load_dataset_dataframe(dataset_id)
    domain = detect_domain(df)["domain"]
    metric = _metric(df, prompt)
    analysis_type = _analysis_type(prompt)
    validation = _logic_validation(df, prompt, metric, analysis_type)
    q = prompt.lower()
    table = _table()
    if not validation["dax_allowed"]:
        dax = "No DAX required - analysis is structural."
    elif "churn" in q:
        churn_col = next((column for column in df.columns if "churn" in column.lower()), None)
        dax = (
            f"Churn Rate =\n"
            f"DIVIDE(\n"
            f"    CALCULATE(COUNTROWS('{table}'), '{table}'[{churn_col or 'Churn'}] = \"Yes\"),\n"
            f"    COUNTROWS('{table}')\n"
            f")"
        )
    elif "ytd" in q and metric:
        dax = f"{metric} YTD =\nTOTALYTD(\n    SUM('{table}'[{metric}]),\n    'Date'[Date]\n)"
    elif "rolling" in q and metric:
        dax = (
            f"Rolling 12 Month {metric} =\n"
            f"CALCULATE(\n"
            f"    SUM('{table}'[{metric}]),\n"
            f"    DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -12, MONTH)\n"
            f")"
        )
    elif "average" in q and metric:
        dax = f"Average {metric} =\nAVERAGE('{table}'[{metric}])"
    elif metric:
        dax = f"Total {metric} =\nSUM('{table}'[{metric}])"
    else:
        dax = "Record Count =\nCOUNTROWS('Dataset')"
    return {
        "prompt": prompt,
        "domain": domain,
        "dax": dax,
        "dax_measure": dax,
        "explanation": explain_dax(dax),
        **_package_with_prompt(dax, domain, metric, prompt, analysis_type, validation),
    }


def explain_dax(dax: str) -> str:
    text = dax.lower()
    parts = ["This DAX measure is designed for a Power BI model using the uploaded dataset as the fact table."]
    if "totalytd" in text:
        parts.append("It calculates year-to-date performance using a Date table.")
    if "datesinperiod" in text:
        parts.append("It calculates a rolling time window for trend analysis.")
    if "divide" in text:
        parts.append("It uses DIVIDE to safely calculate a rate while avoiding divide-by-zero errors.")
    if "calculate" in text:
        parts.append("It applies filter context with CALCULATE.")
    return " ".join(parts)


def optimize_dax(dax: str) -> dict[str, Any]:
    return optimize_dax_with_context(dax, "Generic Analytics", None, "Optimize this DAX measure for executive reporting")


def optimize_dax_with_context(dax: str, domain: str, metric: str | None, prompt: str = "") -> dict[str, Any]:
    optimized = dax.strip()
    analysis_type = _analysis_type(prompt, optimized)
    suggestions = []
    if "/" in optimized and "DIVIDE" not in optimized.upper():
        suggestions.append("Use DIVIDE(numerator, denominator) instead of / for safer rate calculations.")
    if "TOTALYTD" in optimized.upper() and "'Date'[Date]" not in optimized:
        suggestions.append("Use a marked Date table for production YTD calculations.")
    if not suggestions:
        suggestions.append("Formula structure is suitable for a first production measure review.")
    validation = {
        "is_valid": True,
        "dax_allowed": True,
        "field_used": metric or "Inferred from existing DAX",
        "field_type": "numeric" if metric else "unknown",
        "validation_summary": "Existing DAX was optimized structurally. Dataset-level field validation is available in the dataset-aware optimize endpoint.",
        "invalid_reasons": [],
        "warnings": [],
        "should_not_do": [],
    }
    return {
        "dax": optimized,
        "dax_measure": optimized,
        "suggestions": " ".join(suggestions),
        **_package_with_prompt(optimized, domain, metric, prompt, analysis_type, validation),
    }


def optimize_dataset_dax(dataset_id: str, dax: str) -> dict[str, Any]:
    df = load_dataset_dataframe(dataset_id)
    domain = detect_domain(df)["domain"]
    metric = _metric(df, dax)
    analysis_type = _analysis_type("", dax)
    validation = _logic_validation(df, dax, metric, analysis_type)
    result = optimize_dax_with_context(dax, domain, metric, "Optimize this DAX measure for a Power BI dashboard")
    result.update(
        _package_with_prompt(
            result["dax"],
            domain,
            metric,
            "Optimize this DAX measure for a Power BI dashboard",
            analysis_type,
            validation,
        )
    )
    if not validation["dax_allowed"]:
        result["dax"] = "No DAX required - analysis is structural."
        result["dax_measure"] = result["dax"]
        result["dax_output"] = result["dax"]
    return result


def dax_library(dataset_id: str) -> dict[str, Any]:
    df = load_dataset_dataframe(dataset_id)
    domain = detect_domain(df)["domain"]
    metric = _metric(df, "")
    has_date = bool(detect_column_types(df)["date_columns"])
    measures = [
        {"name": "Record Count", "dax": "Record Count =\nCOUNTROWS('Dataset')"},
    ]
    if metric:
        measures.extend(
            [
                {"name": f"Total {metric}", "dax": f"Total {metric} =\nSUM('Dataset'[{metric}])"},
                {"name": f"Average {metric}", "dax": f"Average {metric} =\nAVERAGE('Dataset'[{metric}])"},
            ]
        )
        if has_date:
            measures.extend(
                [
                    {"name": f"{metric} YTD", "dax": f"{metric} YTD =\nTOTALYTD(SUM('Dataset'[{metric}]), 'Date'[Date])"},
                    {"name": f"Rolling 12 Month {metric}", "dax": f"Rolling 12 Month {metric} =\nCALCULATE(SUM('Dataset'[{metric}]), DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -12, MONTH))"},
                ]
            )
    if domain in {"Customer Churn", "Telecom"}:
        measures.append({"name": "Churn Rate", "dax": "Churn Rate =\nDIVIDE(CALCULATE(COUNTROWS('Dataset'), 'Dataset'[Churn] = \"Yes\"), COUNTROWS('Dataset'))"})
    return {"domain": domain, "measures": measures}


def detect_dax_errors(dax: str) -> dict[str, Any]:
    if not dax.strip():
        return {"valid": False, "error": "DAX formula is empty."}
    if dax.count("(") != dax.count(")"):
        return {"valid": False, "error": "Parentheses are not balanced."}
    if re.search(r"\bselect\b|\binsert\b|\bdelete\b", dax, re.I):
        return {"valid": False, "error": "This appears to be SQL, not DAX."}
    return {"valid": True, "error": ""}
