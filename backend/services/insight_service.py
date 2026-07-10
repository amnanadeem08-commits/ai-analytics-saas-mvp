from __future__ import annotations

from functools import lru_cache
import logging
from time import perf_counter

from backend.ai.rule_based_engine import generate_rule_based_insights
from backend.services.analyst.analyst_service import answer_analyst_question
from backend.services.dataset_service import get_dataset_metadata, load_dataset_dataframe
from backend.services.decision_framework_service import build_decision_framework
from backend.services.executive_insight_service import build_executive_summary


logger = logging.getLogger(__name__)


@lru_cache(maxsize=16)
def _get_insights_cached(dataset_id: str, file_hash: str) -> dict:
    del file_hash
    df = load_dataset_dataframe(dataset_id)
    return {
        "dataset_id": dataset_id,
        "insights": generate_rule_based_insights(df),
        "executive_summary": build_executive_summary(df),
    }


def get_insights(dataset_id: str) -> dict:
    started = perf_counter()
    metadata = get_dataset_metadata(dataset_id)
    before = _get_insights_cached.cache_info()
    result = _get_insights_cached(dataset_id, metadata.get("file_hash", ""))
    after = _get_insights_cached.cache_info()
    logger.info("insights_build dataset=%s cache_hit=%s seconds=%.3f", dataset_id, after.hits > before.hits, perf_counter() - started)
    return result


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