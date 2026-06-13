from __future__ import annotations

from backend.ai.rule_based_engine import generate_rule_based_insights
from backend.services.analyst.analyst_service import answer_analyst_question
from backend.services.dataset_service import load_dataset_dataframe
from backend.services.decision_framework_service import build_decision_framework
from backend.services.executive_insight_service import build_executive_summary


def get_insights(dataset_id: str) -> dict:
    df = load_dataset_dataframe(dataset_id)
    insights = generate_rule_based_insights(df)
    return {
        "dataset_id": dataset_id,
        "insights": insights,
        "executive_summary": build_executive_summary(df),
    }


def ask_question(dataset_id: str, question: str) -> dict:
    df = load_dataset_dataframe(dataset_id)
    result = answer_analyst_question(df, question)
    return {
        "dataset_id": dataset_id,
        "question": question,
        "answer": result["answer"],
        "supporting_data": result.get("supporting_data", {}),
        "analyst": result.get("analyst", {}),
    }


def get_decision_framework(dataset_id: str) -> dict:
    df = load_dataset_dataframe(dataset_id)
    return {
        "dataset_id": dataset_id,
        "framework": "what_why_action",
        "decision_blocks": build_decision_framework(df),
    }
