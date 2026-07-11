from __future__ import annotations

"""Analytics helpers shared across API and Streamlit local mode (TD-010)."""

from backend.analytics.insights import (
    build_ai_business_insights_from_data_insights,
    build_data_insights,
)

__all__ = [
    "build_data_insights",
    "build_ai_business_insights_from_data_insights",
]
