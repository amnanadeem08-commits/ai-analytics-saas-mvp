from __future__ import annotations

"""Table helpers — consistent width and empty handling."""

from typing import Any

import pandas as pd
import streamlit as st

from frontend.design_system.alerts import alert


def data_table(
    data: Any,
    *,
    height: int | None = None,
    empty_title: str = "No rows to display",
    empty_body: str = "Adjust filters or load data first.",
) -> None:
    if data is None:
        alert(empty_body, kind="info", title=empty_title)
        return
    if isinstance(data, pd.DataFrame):
        if data.empty:
            alert(empty_body, kind="info", title=empty_title)
            return
        st.dataframe(data, use_container_width=True, height=height)
        return
    if isinstance(data, list):
        if not data:
            alert(empty_body, kind="info", title=empty_title)
            return
        st.dataframe(pd.DataFrame(data), use_container_width=True, height=height)
        return
    st.write(data)
