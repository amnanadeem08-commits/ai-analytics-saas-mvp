from __future__ import annotations

from functools import lru_cache
import logging
from time import perf_counter

from backend.processing.analytics_engine import build_summary
from backend.services.dashboard_service import build_dashboard_view
from backend.services.dataset_service import get_dataset_metadata, load_dataset_dataframe


logger = logging.getLogger(__name__)


@lru_cache(maxsize=16)
def _get_data_summary_cached(dataset_id: str, file_hash: str) -> dict:
    del file_hash
    return {"dataset_id": dataset_id, **build_summary(load_dataset_dataframe(dataset_id))}


def get_data_summary(dataset_id: str) -> dict:
    started = perf_counter()
    metadata = get_dataset_metadata(dataset_id)
    before = _get_data_summary_cached.cache_info()
    result = _get_data_summary_cached(dataset_id, metadata.get("file_hash", ""))
    after = _get_data_summary_cached.cache_info()
    logger.info("summary_build dataset=%s cache_hit=%s seconds=%.3f", dataset_id, after.hits > before.hits, perf_counter() - started)
    return result


def get_dashboard_stats(dataset_id: str) -> dict:
    return build_dashboard_view(dataset_id)


def get_filtered_dashboard_stats(dataset_id: str, filters: dict) -> dict:
    return build_dashboard_view(dataset_id, filters=filters)