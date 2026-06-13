from __future__ import annotations

from typing import Any

import pandas as pd

from backend.services.decision_framework_service import build_decision_framework
from backend.services.analyst.intent_service import detect_intent
from backend.services.analyst.query_service import execute_intent
from backend.services.analyst.response_service import build_answer


def _is_executive_question(question: str) -> bool:
    q = question.lower()
    keywords = [
        "why",
        "caused",
        "cause",
        "drop",
        "decline",
        "growth",
        "churn",
        "risk",
        "risks",
        "prioritize",
        "priority",
        "management",
        "recommend",
        "should we",
        "what should",
        "impact",
    ]
    return any(keyword in q for keyword in keywords)


def _build_executive_answer(df: pd.DataFrame, question: str) -> dict[str, Any] | None:
    if not _is_executive_question(question):
        return None

    blocks = build_decision_framework(df)
    q = question.lower()
    selected = blocks[0] if blocks else None
    if "risk" in q:
        selected = next((block for block in blocks if block.get("severity") == "risk"), selected)
    elif any(word in q for word in ["priority", "prioritize", "recommend", "should"]):
        selected = sorted(blocks, key=lambda block: block.get("priority", 99))[0] if blocks else selected

    if not selected:
        return None

    answer = (
        f"What happened: {selected.get('what_happened', '')} "
        f"Why: {selected.get('why_it_happened', '')} "
        f"What to do: {selected.get('what_to_do', '')} "
        f"Expected impact: {selected.get('expected_impact', '')} "
        f"Confidence: {selected.get('confidence', '')}."
    )
    return {
        "answer": answer,
        "supporting_data": {"selected_block": selected, "decision_blocks": blocks},
        "analyst": {
            "intent": "executive_decision",
            "metric_column": selected.get("metric"),
            "dimension_column": None,
            "confidence": 0.82,
            "render_mode": "decision_framework",
            "rows": blocks,
        },
    }


def answer_analyst_question(df: pd.DataFrame, question: str) -> dict[str, Any]:
    executive_answer = _build_executive_answer(df, question)
    if executive_answer:
        return executive_answer

    intent = detect_intent(question, df)
    result = execute_intent(df, intent)
    answer = build_answer(question, intent, result)
    return {
        "answer": answer,
        "supporting_data": result.supporting_data,
        "analyst": {
            "intent": intent.intent,
            "metric_column": intent.metric_column,
            "dimension_column": intent.dimension_column,
            "confidence": intent.confidence,
            "render_mode": result.render_mode,
            "rows": result.rows,
        },
    }
