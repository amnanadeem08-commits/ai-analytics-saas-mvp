from __future__ import annotations

"""Shared insight builders for API services and Streamlit local mode (TD-010).

Kept outside ``backend.services`` so frontend local-mode may import without
violating PIOS ``FE_NO_BACKEND_SERVICES``. Server-backed datasets must still
use HTTP clients (``BackendClient`` / ``frontend.api``).
"""

from backend.services.ai_business_insight_service import (
    build_ai_business_insights_from_data_insights,
)
from backend.services.data_insights_service import build_data_insights

__all__ = [
    "build_data_insights",
    "build_ai_business_insights_from_data_insights",
]
