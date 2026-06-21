from __future__ import annotations

import io
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import html
import json
from datetime import date
from urllib.parse import urlencode

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from frontend.api_client.backend_client import BackendClient, DEFAULT_API_BASE_URL
from frontend.components.chart_components import (
    render_plotly_chart_specs,
    render_time_trends,
    render_top_categories,
)
from frontend.components.insight_cards import render_insight
from frontend.components.metric_cards import render_summary_metrics


st.set_page_config(page_title="AI Analytics SaaS MVP", layout="wide")


@st.cache_resource
def get_client(base_url: str) -> BackendClient:
    return BackendClient(base_url=base_url)


def safe_table(rows: list[dict]) -> pd.DataFrame:
    """Normalize nested API values so Streamlit/PyArrow can render them."""
    normalized_rows = []
    for row in rows:
        normalized = {}
        for key, value in row.items():
            if isinstance(value, (dict, list)):
                normalized[key] = json.dumps(value, ensure_ascii=False)
            else:
                normalized[key] = value
        normalized_rows.append(normalized)
    return pd.DataFrame(normalized_rows)


def render_backend_status(client: BackendClient) -> None:
    try:
        health = client.health()
        st.sidebar.success(f"Backend connected: {health.get('version', '')}")
    except requests.RequestException:
        st.sidebar.warning("Backend offline. Local CSV preview still works.")


THEME_PRESETS = [
    {"name": "power_bi_professional", "display_name": "Executive Blue", "background": "#F5F7FA", "palette": ["#0078D4", "#004E8C", "#00B7C3", "#F2C811", "#107C10"], "description": "Power BI-style blue palette for executive KPI dashboards."},
    {"name": "financial_intelligence", "display_name": "Emerald Finance", "background": "#07130D", "palette": ["#22C55E", "#16A34A", "#84CC16", "#38BDF8", "#FACC15"], "description": "Finance-ready greens with high-contrast chart accents."},
    {"name": "startup_modern", "display_name": "Purple Modern", "background": "#F8FAFF", "palette": ["#2563EB", "#7C3AED", "#06B6D4", "#10B981", "#F97316"], "description": "Modern pitch-deck palette with purple and blue accents."},
    {"name": "boardroom_dark", "display_name": "Dark Corporate", "background": "#05070B", "palette": ["#60A5FA", "#A78BFA", "#34D399", "#FBBF24", "#F87171"], "description": "Dark boardroom theme for presentation and wall displays."},
    {"name": "minimal_clean", "display_name": "Minimal Gray", "background": "#FAFAFA", "palette": ["#27272A", "#52525B", "#71717A", "#0EA5E9", "#16A34A"], "description": "Clean neutral palette for lightweight business reports."},
]

DEFAULT_BRANDING = {
    "company_name": "AI Analytics",
    "report_title": "Executive Decision Intelligence Report",
    "report_subtitle": "Upload a dataset to generate board-ready KPIs, charts, and insights.",
    "footer_note": "",
    "logo_url": "",
    "primary_color": "#118DFF",
    "secondary_color": "#12239E",
    "accent_color": "#E66C37",
    "theme_name": "power_bi_professional",
}


def initialize_session_state(initial_branding: dict | None = None) -> None:
    """Keep app state stable across navigation, uploads, and theme changes."""
    branding = {**DEFAULT_BRANDING, **(initial_branding or {})}
    st.session_state.setdefault("uploaded_datasets", {})
    st.session_state.setdefault("active_dataset_id", st.session_state.get("selected_dataset_id"))
    st.session_state.setdefault("active_dataframe", None)
    st.session_state.setdefault("selected_theme", branding.get("theme_name", "power_bi_professional"))
    st.session_state.setdefault("branding", branding)
    st.session_state.setdefault("primary_color", branding.get("primary_color", "#118DFF"))
    st.session_state.setdefault("secondary_color", branding.get("secondary_color", "#12239E"))
    st.session_state.setdefault("background_color", "#F5F7FA")
    st.session_state.setdefault("chart_palette", ["#0078D4", "#004E8C", "#00B7C3", "#F2C811", "#107C10"])

    if st.session_state.get("active_dataset_id") and not st.session_state.get("selected_dataset_id"):
        st.session_state["selected_dataset_id"] = st.session_state["active_dataset_id"]

def _render_palette_swatches(palette: list[str]) -> str:
    """Render inline colour swatch HTML for a palette."""
    swatches = "".join(f'<span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:{c};margin-right:3px;border:1px solid rgba(0,0,0,0.08)"></span>' for c in palette)
    return swatches


def render_theme_selector(client: BackendClient) -> None:
    st.sidebar.markdown("#### Theme Gallery")
    payload: dict = {"active_theme": None, "themes": []}
    try:
        payload = client.list_themes()
    except requests.RequestException:
        st.sidebar.caption("Start the backend to apply saved theme presets.")

    active_name = st.session_state.get("selected_theme") or payload.get("active_theme")

    for preset in THEME_PRESETS:
        swatches = _render_palette_swatches(preset["palette"])
        is_active = preset["name"] == active_name
        st.sidebar.markdown(
            f"""
            <div style="
                padding:6px 8px;
                margin:2px 0;
                border-radius:6px;
                border:1px solid {'#118DFF' if is_active else 'transparent'};
                background:{'rgba(17,141,255,0.06)' if is_active else 'transparent'};
                cursor:pointer;
                font-size:0.85rem;
            ">
                <div style="display:flex;align-items:center;gap:6px;">
                    <span>{swatches}</span>
                    <span style="font-weight:{600 if is_active else 400};">{preset['display_name']}</span>
                </div>
                <div style="font-size:0.7rem;color:#64748B;margin-top:2px;">{preset['description']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.sidebar.button("Apply", key=f"theme_{preset['name']}", use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state["selected_theme"] = preset["name"]
            st.session_state["primary_color"] = preset["palette"][0]
            st.session_state["secondary_color"] = preset["palette"][1]
            st.session_state["background_color"] = preset["background"]
            st.session_state["chart_palette"] = preset["palette"]
            current_branding = {**st.session_state.get("branding", DEFAULT_BRANDING)}
            current_branding.update(
                {
                    "primary_color": preset["palette"][0],
                    "secondary_color": preset["palette"][1],
                    "accent_color": preset["palette"][2],
                    "theme_name": preset["name"],
                }
            )
            st.session_state["branding"] = current_branding
            try:
                applied_theme = client.set_active_theme(preset["name"])
                st.session_state["primary_color"] = applied_theme.get("primary", preset["palette"][0])
                st.session_state["secondary_color"] = applied_theme.get("secondary", preset["palette"][1])
                st.session_state["background_color"] = applied_theme.get("background", preset["background"])
                st.session_state["chart_palette"] = applied_theme.get("palette", preset["palette"])
                current_branding.update(
                    {
                        "primary_color": st.session_state["primary_color"],
                        "secondary_color": st.session_state["secondary_color"],
                        "accent_color": applied_theme.get("accent", preset["palette"][2]),
                        "theme_name": preset["name"],
                    }
                )
                st.session_state["branding"] = current_branding
                client.update_branding(
                    {
                        "primary_color": current_branding["primary_color"],
                        "secondary_color": current_branding["secondary_color"],
                        "accent_color": current_branding["accent_color"],
                        "theme_name": preset["name"],
                    }
                )
            except requests.RequestException as exc:
                st.sidebar.error(f"Could not switch theme: {exc}")
            st.rerun()


def get_active_branding(client: BackendClient) -> dict:
    try:
        return client.get_branding()
    except requests.RequestException:
        return {
            "company_name": "AI Analytics",
            "report_title": "Executive Decision Intelligence Report",
            "report_subtitle": "Upload a dataset to generate board-ready KPIs, charts, and insights.",
            "footer_note": "",
            "logo_url": "",
            "primary_color": "#118DFF",
            "secondary_color": "#12239E",
            "accent_color": "#E66C37",
            "theme_name": "power_bi_professional",
        }


def render_branding_editor(client: BackendClient, branding: dict) -> None:
    st.sidebar.divider()
    with st.sidebar.expander("Branding Settings", expanded=False):
        logo_url = branding.get("logo_url")
        if logo_url:
            st.image(f"{client.base_url}{logo_url}", width=100)

        company_name = st.text_input("Company name", value=branding.get("company_name", "AI Analytics"))
        report_title = st.text_input(
            "Report title",
            value=branding.get("report_title", "Executive Decision Intelligence Report"),
        )
        report_subtitle = st.text_input(
            "Subtitle",
            value=branding.get("report_subtitle", "Upload a dataset to generate board-ready KPIs, charts, and insights."),
        )
        footer_note = st.text_area(
            "Footer / brand note",
            value=branding.get("footer_note", ""),
            height=80,
        )
        logo_file = st.file_uploader("Upload Company Logo", type=["png", "jpg", "jpeg", "webp", "svg"], key="branding_logo_upload")
        primary_color = branding.get("primary_color", "#118DFF")
        secondary_color = branding.get("secondary_color", "#12239E")
        accent_color = branding.get("accent_color", "#E66C37")
        st.caption("Theme preset colors are managed from Theme Gallery.")

        col1, col2 = st.columns(2)
        if col1.button("Save", use_container_width=True, key="branding_save_button"):
            branding_payload = {
                "company_name": company_name,
                "report_title": report_title,
                "report_subtitle": report_subtitle,
                "footer_note": footer_note,
                "primary_color": primary_color,
                "secondary_color": secondary_color,
                "accent_color": accent_color,
            }
            st.session_state["branding"] = {**st.session_state.get("branding", DEFAULT_BRANDING), **branding_payload}
            try:
                client.update_branding(branding_payload)
                if logo_file is not None:
                    st.session_state["branding"] = client.upload_logo(logo_file)
                st.rerun()
            except requests.RequestException as exc:
                st.warning(f"Could not save branding right now: {exc}")
        if col2.button("Reset", use_container_width=True, key="branding_reset_button"):
            reset_payload = {
                "company_name": "AI Analytics",
                "report_title": "Executive Decision Intelligence Report",
                "report_subtitle": "Upload a dataset to generate board-ready KPIs, charts, and insights.",
                "footer_note": "",
                "logo_url": "",
                "primary_color": "#118DFF",
                "secondary_color": "#12239E",
                "accent_color": "#E66C37",
                "theme_name": "power_bi_professional",
            }
            st.session_state["branding"] = {**DEFAULT_BRANDING, **reset_payload}
            try:
                client.update_branding(reset_payload)
                st.rerun()
            except requests.RequestException as exc:
                st.warning(f"Could not reset branding right now: {exc}")


def get_dataset_options(client: BackendClient) -> list[dict]:
    try:
        datasets = client.list_datasets()
    except requests.RequestException:
        datasets = []
    for item in datasets:
        dataset_id = item.get("dataset_id")
        if dataset_id:
            st.session_state["uploaded_datasets"].setdefault(dataset_id, item)
    return datasets


def select_dataset(client: BackendClient, key: str | None = None) -> str | None:
    datasets = get_dataset_options(client)
    if not datasets:
        st.info("No datasets found. Upload a CSV first.")
        return None

    labels = {
        f"{item['original_filename']} — {item['dataset_id']}": item["dataset_id"]
        for item in datasets
    }

    default_label = None
    selected_id = st.session_state.get("active_dataset_id") or st.session_state.get("selected_dataset_id")
    for label, dataset_id in labels.items():
        if dataset_id == selected_id:
            default_label = label
            break

    label_list = list(labels.keys())
    index = label_list.index(default_label) if default_label in label_list else 0
    selected_label = st.selectbox("Select dataset", label_list, index=index, key=key or "select_dataset_default")
    dataset_id = labels[selected_label]
    st.session_state["active_dataset_id"] = dataset_id
    st.session_state["selected_dataset_id"] = dataset_id
    return dataset_id


def _read_uploaded_dataframe(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    content = uploaded_file.getvalue()
    buffer = io.BytesIO(content)
    if suffix in {".xlsx", ".xlsm"}:
        try:
            return pd.read_excel(buffer)
        except Exception:
            # Some exports are CSV data with an Excel-like extension.
            buffer.seek(0)
            return pd.read_csv(buffer)

    for encoding in ("utf-8", "utf-8-sig", "latin1"):
        try:
            return pd.read_csv(io.BytesIO(content), encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(io.BytesIO(content))


def _local_summary(df: pd.DataFrame) -> dict:
    missing = int(df.isna().sum().sum())
    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "total_missing_values": missing,
        "duplicate_rows": int(df.duplicated().sum()),
        "column_types": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "missing_values_by_column": df.isna().sum().astype(int).to_dict(),
    }


def _render_local_kpis(df: pd.DataFrame, numeric_columns: list[str]) -> None:
    st.subheader("Dashboard Cards")
    if not numeric_columns:
        cols = st.columns(3)
        cols[0].metric("Rows", f"{len(df):,}")
        cols[1].metric("Columns", f"{len(df.columns):,}")
        cols[2].metric("Duplicates", f"{df.duplicated().sum():,}")
        return

    default_kpis = numeric_columns[: min(4, len(numeric_columns))]
    selected_kpis = st.multiselect("Select KPI columns", numeric_columns, default=default_kpis, key="local_kpi_columns")
    if not selected_kpis:
        st.info("Select one or more numeric columns to show KPI cards.")
        return

    cols = st.columns(min(4, len(selected_kpis)))
    for col, column in zip(cols, selected_kpis):
        series = pd.to_numeric(df[column], errors="coerce")
        col.metric(column, f"{series.sum():,.2f}", f"Avg {series.mean():,.2f}")


def _render_local_chart_builder(df: pd.DataFrame, palette: list[str]) -> None:
    st.subheader("Chart Preview")
    if df.empty:
        st.info("The uploaded dataset has no rows to chart.")
        return

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    columns = df.columns.tolist()
    if not columns:
        st.info("The uploaded dataset has no columns to chart.")
        return

    settings, canvas = st.columns([1, 2])
    with settings:
        chart_type = st.selectbox("Chart type", ["Bar", "Line", "Scatter", "Pie", "Table"], key="local_chart_type")
        x_axis = st.selectbox("X-axis", columns, key="local_x_axis")
        y_options = ["Record Count"] + numeric_columns
        y_axis = st.selectbox("Y-axis", y_options, key="local_y_axis")
        aggregation = st.selectbox("Aggregation", ["sum", "mean", "count", "min", "max"], key="local_chart_aggregation")

    if y_axis == "Record Count":
        grouped = df.groupby(x_axis, dropna=False).size().reset_index(name="Record Count")
        value_column = "Record Count"
    else:
        grouped = (
            df.groupby(x_axis, dropna=False)[y_axis]
            .agg(aggregation)
            .reset_index()
            .rename(columns={y_axis: f"{aggregation.title()} {y_axis}"})
        )
        value_column = f"{aggregation.title()} {y_axis}"

    grouped[x_axis] = grouped[x_axis].astype(str)
    grouped = grouped.sort_values(value_column, ascending=False).head(50)

    with canvas:
        if chart_type == "Table":
            st.dataframe(grouped, use_container_width=True, hide_index=True)
            return

        title = f"{value_column} by {x_axis}"
        if chart_type == "Pie":
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=grouped[x_axis],
                        values=grouped[value_column],
                        hole=0.38,
                        marker={"colors": palette[: len(grouped)]},
                    )
                ]
            )
        elif chart_type == "Line":
            fig = go.Figure(data=[go.Scatter(x=grouped[x_axis], y=grouped[value_column], mode="lines+markers", line={"color": palette[0]})])
        elif chart_type == "Scatter":
            fig = go.Figure(data=[go.Scatter(x=grouped[x_axis], y=grouped[value_column], mode="markers", marker={"color": palette[0], "size": 10})])
        else:
            fig = go.Figure(data=[go.Bar(x=grouped[x_axis], y=grouped[value_column], marker={"color": palette[: len(grouped)]})])
        fig.update_layout(title=title, height=430, margin={"l": 48, "r": 24, "t": 64, "b": 96})
        fig.update_xaxes(automargin=True)
        fig.update_yaxes(automargin=True)
        st.plotly_chart(fig, use_container_width=True)


def _render_local_dataset_workbench(df: pd.DataFrame, filename: str, branding: dict) -> None:
    st.success(f"Previewing local dataset: {filename}")
    summary = _local_summary(df)
    render_summary_metrics(summary)

    rows = st.slider("Preview rows", min_value=5, max_value=100, value=min(10, max(5, len(df))), step=5, key="local_preview_rows")
    st.subheader("Preview")
    st.dataframe(df.head(rows), use_container_width=True)

    with st.expander("Column Schema", expanded=False):
        schema = pd.DataFrame(
            [{"column": column, "dtype": str(dtype), "missing": int(df[column].isna().sum())} for column, dtype in df.dtypes.items()]
        )
        st.dataframe(schema, use_container_width=True, hide_index=True)

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    palette = [
        branding.get("primary_color", "#0078D4"),
        branding.get("secondary_color", "#004E8C"),
        branding.get("accent_color", "#F2C811"),
        "#10B981",
        "#F97316",
    ]
    _render_local_kpis(df, numeric_columns)
    _render_local_chart_builder(df, palette)


def render_dataset_upload_area(client: BackendClient) -> None:
    with st.container(border=True):
        st.subheader("Upload CSV Dataset")
        st.caption("Upload data here. Logo upload lives only in Branding Settings.")
        uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx", "xlsm"], key="dataset_upload_main")
        if uploaded_file is None:
            return

        st.caption(f"Selected file: {uploaded_file.name}")
        if st.button("Upload and Preview Dataset", type="primary", use_container_width=True):
            try:
                local_df = _read_uploaded_dataframe(uploaded_file)
                local_dataset_id = f"local::{uploaded_file.name}"
                local_dataset = {"dataset_id": local_dataset_id, "original_filename": uploaded_file.name, "dataframe": local_df}
                st.session_state["uploaded_datasets"][local_dataset_id] = local_dataset
                st.session_state["active_dataset_id"] = local_dataset_id
                st.session_state["selected_dataset_id"] = local_dataset_id
                st.session_state["active_dataframe"] = local_df
                st.session_state["local_uploaded_dataset"] = {"filename": uploaded_file.name, "dataframe": local_df}
            except Exception as exc:
                st.warning(f"Could not preview this file locally. Check that it is a valid CSV or Excel file. Details: {exc}")
                return

            try:
                result = client.upload_csv(uploaded_file)
                st.success(result.get("message", "Dataset uploaded."))
                backend_dataset_id = result["dataset_id"]
                st.session_state["uploaded_datasets"][backend_dataset_id] = {
                    "dataset_id": backend_dataset_id,
                    "original_filename": uploaded_file.name,
                    "dataframe": local_df,
                }
                st.session_state["active_dataset_id"] = backend_dataset_id
                st.session_state["selected_dataset_id"] = backend_dataset_id
                st.session_state["active_dataframe"] = local_df
                st.rerun()
            except requests.RequestException as exc:
                st.info(f"Backend upload is unavailable, so the local preview is shown instead. Details: {exc}")


def render_dataset_overview(client: BackendClient) -> None:
    st.header("Dataset Preview")
    branding = st.session_state.get("branding", DEFAULT_BRANDING)
    render_dataset_upload_area(client)
    st.divider()

    dataset_id = select_dataset(client, key="dataset_preview_select")
    if not dataset_id:
        local_dataset = st.session_state.get("local_uploaded_dataset")
        if local_dataset:
            _render_local_dataset_workbench(local_dataset["dataframe"], local_dataset["filename"], branding)
        return

    if str(dataset_id).startswith("local::"):
        active_df = st.session_state.get("active_dataframe")
        local_dataset = st.session_state.get("uploaded_datasets", {}).get(dataset_id, {})
        if active_df is not None:
            _render_local_dataset_workbench(active_df, local_dataset.get("original_filename", "Uploaded dataset"), branding)
        else:
            st.info("Upload a dataset first from Dataset Preview.")
        return

    rows = st.slider("Preview rows", min_value=5, max_value=100, value=10, step=5)
    try:
        overview = client.get_overview(dataset_id)
        preview = client.get_preview(dataset_id, rows=rows)
        summary_cols = st.columns(4)
        summary_cols[0].metric("Rows", f"{overview.get('row_count', 0):,}")
        summary_cols[1].metric("Columns", f"{overview.get('column_count', 0):,}")
        summary_cols[2].metric(
            "Completeness",
            f"{overview.get('missing_summary', {}).get('completeness_pct', 0)}%",
        )
        summary_cols[3].metric("Duplicates", f"{overview.get('duplicate_rows', 0):,}")
        st.subheader("Column Schema")
        st.dataframe(pd.DataFrame(overview.get("column_schema", [])), use_container_width=True)
        st.subheader("Preview")
        st.dataframe(pd.DataFrame(preview["rows"]), use_container_width=True)
    except requests.RequestException as exc:
        st.warning(f"Could not load backend preview. Showing local preview if available. Details: {exc}")
        local_dataset = st.session_state.get("local_uploaded_dataset")
        if local_dataset:
            _render_local_dataset_workbench(local_dataset["dataframe"], local_dataset["filename"], branding)


def _build_filter_payload(schema: dict, key_prefix: str) -> dict:
    filters: dict = {}
    options = schema.get("filters", {})
    categorical = {
        name: cfg
        for name, cfg in options.items()
        if cfg.get("type") in {"categorical", "boolean"} and cfg.get("values")
    }
    if not categorical:
        return filters

    with st.expander("Filters", expanded=False):
        for column, cfg in categorical.items():
            selected = st.multiselect(
                column,
                cfg.get("values", []),
                key=f"{key_prefix}_filter_{column}",
            )
            if selected:
                filters[column] = {"values": selected}
    return filters


def _format_active_filter(column: str, criteria: dict) -> str:
    if criteria.get("values"):
        return f"{column}: {', '.join(map(str, criteria['values']))}"
    if criteria.get("min") is not None or criteria.get("max") is not None:
        return f"{column}: {criteria.get('min', 'Any')} - {criteria.get('max', 'Any')}"
    return column


def _dashboard_studio_slicer_payload(schema: dict, dataset_id: str) -> dict:
    filters: dict = {}
    options = schema.get("filters", {})
    recommendations = schema.get("slicer_recommendations", [])
    recommended_fields = [item["field"] for item in recommendations if item.get("field") in options]
    all_fields = list(options.keys())
    state_prefix = f"dashboard_studio_{dataset_id}"
    selected_key = f"{state_prefix}_slicer_fields"

    if selected_key not in st.session_state:
        st.session_state[selected_key] = recommended_fields[:4]

    st.subheader("Slicers")
    st.selectbox("Apply slicers to", ["All visuals"], index=0)
    st.caption("Slicers currently apply to all Dashboard Studio visuals.")

    left, right = st.columns([3, 1])
    selected_fields = left.multiselect(
        "Choose slicer fields",
        all_fields,
        default=[field for field in st.session_state[selected_key] if field in all_fields],
        key=f"{state_prefix}_slicer_field_picker",
        help="Recommended slicers avoid high-cardinality ID columns by default, but you can manually choose any field.",
    )
    st.session_state[selected_key] = selected_fields
    if right.button("Reset Filters", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith(f"{state_prefix}_slicer_"):
                del st.session_state[key]
        st.session_state[selected_key] = recommended_fields[:4]
        st.rerun()

    if recommendations:
        with st.expander("Recommended Slicer Fields", expanded=False):
            rows = [
                {
                    "Field": item.get("field"),
                    "Slicer Type": item.get("slicer_type"),
                    "Semantic Role": item.get("semantic_role"),
                    "Why Useful": item.get("reason"),
                }
                for item in recommendations
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if not selected_fields:
        st.info("No slicers selected. Add country, gender, category, segment, date, or numeric fields to filter visuals.")

    for column in selected_fields:
        cfg = options.get(column, {})
        filter_type = cfg.get("type")
        key_base = f"{state_prefix}_slicer_{column}"
        if filter_type in {"categorical", "boolean"}:
            values = cfg.get("values", [])
            mode = st.radio(
                f"{column} slicer type",
                ["Multi-select", "Dropdown"],
                horizontal=True,
                key=f"{key_base}_mode",
            )
            if mode == "Dropdown":
                selected_value = st.selectbox(f"Dropdown slicer: {column}", ["All"] + values, key=f"{key_base}_dropdown")
                if selected_value != "All":
                    filters[column] = {"values": [selected_value]}
            else:
                selected_values = st.multiselect(f"Multi-select slicer: {column}", values, key=f"{key_base}_multi")
                if selected_values:
                    filters[column] = {"values": selected_values}
        elif filter_type == "date_range":
            min_date = pd.to_datetime(cfg.get("min")).date() if cfg.get("min") else date.today()
            max_date = pd.to_datetime(cfg.get("max")).date() if cfg.get("max") else min_date
            selected_range = st.date_input(
                f"Date range slicer: {column}",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key=f"{key_base}_date_range",
            )
            if isinstance(selected_range, tuple) and len(selected_range) == 2:
                start, end = selected_range
                if start != min_date or end != max_date:
                    filters[column] = {"min": start.isoformat(), "max": end.isoformat()}
        elif filter_type == "numeric_range":
            min_value = float(cfg.get("min", 0) or 0)
            max_value = float(cfg.get("max", min_value) or min_value)
            if min_value == max_value:
                st.caption(f"{column} has one numeric value: {min_value:g}")
                continue
            selected_min, selected_max = st.slider(
                f"Numeric range slicer: {column}",
                min_value=min_value,
                max_value=max_value,
                value=(min_value, max_value),
                key=f"{key_base}_numeric_range",
            )
            if selected_min != min_value or selected_max != max_value:
                filters[column] = {"min": selected_min, "max": selected_max}

    st.markdown("**Active Filters**")
    if filters:
        for column, criteria in filters.items():
            st.caption(_format_active_filter(column, criteria))
    else:
        st.caption("No filters applied.")
    return filters


def _sparkline_html(values: list) -> str:
    numeric = [float(value) for value in values if isinstance(value, (int, float))]
    if not numeric:
        return ""
    max_value = max(abs(value) for value in numeric) or 1
    bars = []
    for value in numeric[-8:]:
        height = max(14, int(abs(value) / max_value * 34))
        bars.append(f'<span class="spark-bar" style="height:{height}px"></span>')
    return f'<div class="sparkline">{"".join(bars)}</div>'


def _kpi_icon_svg(icon: str) -> str:
    paths = {
        "table": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>',
        "shield": '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6l7-3z"/><path d="M9 12l2 2 4-5"/>',
        "chart": '<path d="M4 19h16"/><rect x="6" y="10" width="3" height="7"/><rect x="11" y="6" width="3" height="11"/><rect x="16" y="12" width="3" height="5"/>',
        "users": '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2"/><path d="M3 19c1-4 4-6 6-6s5 2 6 6"/><path d="M14 15c2 0 4 1 5 4"/>',
        "metric": '<path d="M4 17l5-5 3 3 7-8"/><path d="M15 7h4v4"/>',
    }
    path = paths.get(icon, paths["metric"])
    return f'<svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">{path}</svg>'


def _render_kpi_cards(cards: list[dict], theme: dict | None = None) -> None:
    if not cards:
        return
    theme = theme or {}
    surface = theme.get("surface", "#FFFFFF")
    border = theme.get("border", "#D7DEE8")
    muted = theme.get("muted_text", "#64748B")
    text = theme.get("text", "#111827")
    shadow = "0 10px 24px rgba(15, 23, 42, 0.06)" if theme.get("mode") != "dark" else "0 10px 24px rgba(0, 0, 0, 0.28)"
    st.markdown(
        f"""
        <style>
        :root {{
            --kpi-surface: {surface};
            --kpi-border: {border};
            --kpi-muted: {muted};
            --kpi-text: {text};
            --kpi-shadow: {shadow};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        .kpi-card {
            border: 1px solid var(--kpi-border);
            border-radius: 10px;
            padding: 14px 16px 16px;
            min-height: 198px;
            background: var(--kpi-surface);
            box-shadow: var(--kpi-shadow);
        }
        .kpi-topline {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }
        .kpi-icon {
            width: 22px;
            height: 22px;
        }
        .kpi-label {
            font-size: 0.78rem;
            color: var(--kpi-muted);
            text-transform: uppercase;
            letter-spacing: 0;
            font-weight: 700;
        }
        .kpi-value {
            font-size: 1.55rem;
            color: var(--kpi-text);
            font-weight: 800;
            margin-top: 6px;
        }
        .kpi-delta {
            font-size: 0.86rem;
            margin-top: 8px;
            font-weight: 700;
        }
        .kpi-context {
            font-size: 0.78rem;
            color: var(--kpi-muted);
            margin-top: 8px;
            line-height: 1.25;
        }
        .sparkline {
            display: flex;
            align-items: flex-end;
            gap: 3px;
            height: 38px;
            margin-top: 8px;
        }
        .spark-bar {
            display: inline-block;
            width: 8px;
            border-radius: 3px 3px 0 0;
            background: currentColor;
            opacity: 0.72;
        }
        .kpi-decision {
            font-size: 0.72rem;
            color: var(--kpi-muted);
            margin-top: 8px;
            line-height: 1.25;
        }
        .kpi-meta {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
            font-size: 0.7rem;
            color: var(--kpi-muted);
        }
        .risk-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 5px;
            background: currentColor;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    for offset in range(0, min(len(cards), 8), 4):
        cols = st.columns(4)
        for col, card in zip(cols, cards[offset : offset + 4]):
            value = card.get("value", "")
            if card.get("format") == "percent" and isinstance(value, (int, float)):
                value = f"{value}%"
            delta = card.get("delta_percentage")
            delta_text = "No prior comparison" if delta is None else f"{card.get('trend_arrow', '->')} {delta}%"
            color = card.get("status_color") or muted
            context = card.get("business_context") or card.get("description") or ""
            sparkline = _sparkline_html(card.get("sparkline", []))
            reason = card.get("reason", "")
            action = card.get("recommended_action", "")
            impact = card.get("expected_impact", "")
            icon = _kpi_icon_svg(card.get("icon", "metric"))
            risk = card.get("risk_indicator", "normal")
            confidence = card.get("confidence_score", 0.75)
            col.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-topline">
                        <div class="kpi-label">{card.get('label', 'Metric')}</div>
                        <div style="color: {color};">{icon}</div>
                    </div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-delta" style="color: {color};">{delta_text}</div>
                    <div style="color: {color};">{sparkline}</div>
                    <div class="kpi-meta">
                        <span style="color: {color};"><span class="risk-dot"></span>{risk.title()}</span>
                        <span>Confidence {round(float(confidence) * 100)}%</span>
                    </div>
                    <div class="kpi-context">{context}</div>
                    <div class="kpi-decision"><b>Reason:</b> {reason}</div>
                    <div class="kpi-decision"><b>Action:</b> {action}</div>
                    <div class="kpi-decision"><b>Impact:</b> {impact}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_dashboard_header(dashboard: dict, summary: dict) -> None:
    branding = dashboard.get("branding", {})
    theme = dashboard.get("theme", {})
    title = html.escape(branding.get("report_title", "Executive Analytics Dashboard"))
    company = html.escape(branding.get("company_name", "AI Analytics"))
    primary = theme.get("primary", "#118DFF")
    muted = theme.get("muted_text", "#64748B")
    rows = dashboard.get("filtered_row_count", summary.get("row_count", 0))
    cols = summary.get("column_count", dashboard.get("overview", {}).get("column_count", 0))
    charts = len(dashboard.get("chart_specs", []))
    st.markdown(
        f"""
        <div style="
            border: 1px solid rgba(148,163,184,0.26);
            border-radius: 10px;
            padding: 18px 20px;
            margin-bottom: 16px;
            background: linear-gradient(135deg, rgba(17,141,255,0.10), rgba(255,255,255,0.02));
        ">
            <div style="font-size:0.76rem;font-weight:800;color:{primary};text-transform:uppercase;">{company}</div>
            <div style="font-size:1.55rem;font-weight:850;color:var(--text-color);margin-top:2px;">{title}</div>
            <div style="font-size:0.88rem;color:{muted};margin-top:6px;">
                {rows:,} active records · {cols:,} columns · {charts:,} generated visuals
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_data_quality_panel(summary: dict, dashboard: dict) -> None:
    missing = int(summary.get("total_missing_values", 0) or 0)
    duplicates = int(summary.get("duplicate_rows", 0) or 0)
    row_count = int(summary.get("row_count", 0) or 0)
    column_count = int(summary.get("column_count", 0) or 0)
    total_cells = max(row_count * column_count, 1)
    completeness = round((1 - missing / total_cells) * 100, 2)
    grade = "A" if completeness >= 98 and duplicates == 0 else "B" if completeness >= 92 else "C" if completeness >= 80 else "D"
    status = "Production-ready" if grade == "A" else "Review recommended"
    analysis_guardrails = dashboard.get("analysis_guardrails", {})
    with st.container(border=True):
        st.markdown("#### Data Quality")
        cols = st.columns([1, 1, 1, 2])
        cols[0].metric("Grade", grade)
        cols[1].metric("Completeness", f"{completeness}%")
        cols[2].metric("Duplicates", f"{duplicates:,}")
        cols[3].write(f"**Status:** {status}")
        if missing:
            cols[3].caption(f"{missing:,} missing cells may affect charts and KPI confidence.")
        else:
            cols[3].caption("No missing cells detected in the current dataset view.")
        invalid = analysis_guardrails.get("invalid_methods", [])
        if invalid:
            with st.expander("Analysis guardrails"):
                for item in invalid:
                    st.write(f"- {item}")


def _render_business_summary(dashboard: dict, insights_payload: dict | None = None) -> None:
    executive = (insights_payload or {}).get("executive_summary") or {}
    domain = dashboard.get("domain_intelligence", {}).get("detection", {})
    with st.container(border=True):
        st.markdown("#### Executive Summary")
        if domain:
            st.caption(f"Detected domain: {domain.get('domain', 'Generic Analytics')} · Confidence: {domain.get('confidence', 'low').title()}")
        if not executive:
            st.info("Executive summary is not available yet. Upload a dataset with measurable fields to generate one.")
            return
        st.markdown(f"**Insight:** {executive.get('insight', '')}")
        st.write(f"**Why it matters:** {executive.get('reason', '')}")
        st.write(f"**Recommended action:** {executive.get('action', '')}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Data confidence", str(executive.get("data_confidence", executive.get("confidence", "low"))).title())
        c2.metric("Business confidence", str(executive.get("business_confidence", "medium")).title())
        c3.metric("Business relevance", str(executive.get("business_relevance", "medium")).title())
        evidence = executive.get("evidence", [])
        if evidence:
            with st.expander("Evidence"):
                for item in evidence[:8]:
                    st.write(f"- {item}")


def _render_suggested_questions(dashboard: dict) -> None:
    backend_questions = dashboard.get("suggested_questions") or []
    if backend_questions:
        questions = backend_questions
    else:
        questions = []
        metrics = dashboard.get("business_metrics", {})
        metric = metrics.get("primary_metric")
        segment = metrics.get("primary_segment")
        if metric and segment:
            questions.extend(
                [
                    f"Which {segment} has the strongest {metric} performance?",
                    f"Why is {metric} different across {segment}?",
                    f"What should management do to improve {metric}?",
                ]
            )
        elif metric:
            questions.extend(
                [
                    f"What is the trend in {metric}?",
                    f"Which columns explain changes in {metric}?",
                ]
            )
        questions.append("What risks should leadership watch in this dataset?")
    with st.container(border=True):
        st.markdown("#### Suggested Questions")
        for question in questions[:5]:
            st.write(f"- {question}")


def _render_dashboard_preview(preview_rows: list[dict]) -> None:
    with st.expander("Dataset preview", expanded=False):
        if preview_rows:
            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True)
        else:
            st.info("No preview rows are available for this dataset.")


def render_dashboard(client: BackendClient) -> None:
    st.header("Executive Dashboard")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    try:
        summary = client.get_summary(dataset_id)
        preview = client.get_preview(dataset_id, rows=8)
        insights_payload = client.get_insights(dataset_id)
        schema = client.get_visual_builder_schema(dataset_id)
        filters = _build_filter_payload(schema, "dashboard")
        dashboard = (
            client.get_filtered_dashboard(dataset_id, filters)
            if filters
            else client.get_dashboard(dataset_id)
        )
    except requests.RequestException as exc:
        st.warning(f"Could not load analytics right now: {exc}")
        return

    _render_dashboard_header(dashboard, summary)
    render_summary_metrics(summary)
    _render_dashboard_preview(preview.get("rows", []))
    _render_business_summary(dashboard, insights_payload)
    _render_kpi_cards(dashboard.get("kpi_cards", []), dashboard.get("theme", {}))

    if dashboard.get("filtered"):
        st.caption(
            f"Filtered rows: {dashboard.get('filtered_row_count', 0):,} of "
            f"{dashboard.get('original_row_count', 0):,}"
        )

    _render_data_quality_panel(summary, dashboard)

    with st.expander("Column profile", expanded=False):
        col_types = summary.get("column_types", {})
        st.json(col_types)
        numeric_summary = summary.get("numeric_summary", {})
        if numeric_summary:
            st.dataframe(pd.DataFrame(numeric_summary).T, use_container_width=True)
        missing_values = summary.get("missing_values_by_column", {})
        if missing_values:
            missing_df = pd.DataFrame(
                [{"column": key, "missing_values": value} for key, value in missing_values.items()]
            )
            st.dataframe(missing_df, use_container_width=True)

    st.subheader("Visual Analysis")
    render_plotly_chart_specs(dashboard)

    left, right = st.columns(2)
    with left:
        _render_suggested_questions(dashboard)
    with right:
        with st.container(border=True):
            st.markdown("#### Business Insights")
            for insight in insights_payload.get("insights", [])[:4]:
                render_insight(insight)


def render_ai_insights(client: BackendClient) -> None:
    st.header("Natural Language Business Insights")
    dataset_id = st.session_state.get("active_dataset_id") or st.session_state.get("selected_dataset_id")
    if not dataset_id:
        st.info("Upload a dataset first from Dataset Preview.")
        return
    if str(dataset_id).startswith("local::"):
        st.info("Upload a dataset first from Dataset Preview.")
        st.caption("Local preview data is still available in Dataset Preview. Start the backend and upload the dataset there to generate AI insights.")
        return

    try:
        insight_payload = client.get_insights(dataset_id)
        domain_payload = client.get_domain_intelligence(dataset_id)
        insights = insight_payload.get("insights", [])
    except requests.RequestException as exc:
        st.warning(f"Could not load insights right now: {exc}")
        return

    detection = domain_payload.get("detection", {})
    st.subheader("Domain Intelligence")
    cols = st.columns(3)
    cols[0].metric("Detected Domain", detection.get("domain", "Generic Analytics"))
    cols[1].metric("Confidence", detection.get("confidence", "low").title())
    cols[2].metric("Domain KPIs", len(domain_payload.get("domain_kpis", [])))
    st.caption(detection.get("business_context", ""))

    domain_mode = domain_payload.get("domain_mode", {})
    if domain_mode.get("available"):
        with st.expander(f"{domain_mode.get('mode', '').title()} Analytics Mode", expanded=True):
            st.write(f"**What happened:** {domain_mode.get('what_happened', '')}")
            st.write(f"**Why it happened:** {domain_mode.get('why_it_happened', '')}")
            st.write(f"**What to do:** {domain_mode.get('what_to_do', '')}")
            st.write(f"**Expected impact:** {domain_mode.get('expected_impact', '')}")
            st.json({key: value for key, value in domain_mode.items() if key not in {'what_happened', 'why_it_happened', 'what_to_do', 'expected_impact'}})

    root_causes = domain_payload.get("root_causes", [])
    if root_causes:
        with st.expander("Root Cause Engine", expanded=True):
            st.dataframe(safe_table(root_causes), use_container_width=True)

    executive = insight_payload.get("executive_summary")
    if executive:
        st.subheader("Executive Summary")
        st.info(f"**Insight**\n\n{executive.get('insight', '')}")
        st.write(f"**Reason:** {executive.get('reason', '')}")
        st.write(f"**Action:** {executive.get('action', '')}")
        ceo_insights = executive.get("ceo_insights", [])
        if ceo_insights:
            st.subheader("CEO Insight Framework")
            for item in ceo_insights:
                with st.expander(item.get("metric", "Metric"), expanded=True):
                    st.write(f"**What happened:** {item.get('what_happened', '')}")
                    st.write(f"**Why it happened:** {item.get('why_it_happened', '')}")
                    st.write(f"**What to do:** {item.get('what_to_do', '')}")
                    st.write(f"**Expected impact:** {item.get('expected_impact', '')}")
                    st.write(f"**Confidence:** {item.get('confidence', '')}")
        with st.expander("Evidence"):
            for item in executive.get("evidence", []):
                st.write(f"- {item}")

    st.subheader("Rule-Based Insights")
    for insight in insights:
        render_insight(insight)

    st.subheader("Ask a Question")
    question = st.text_input(
        "Ask about this dataset",
        placeholder="Example: Which product has the highest sales?",
    )

    if st.button("Ask", disabled=not question.strip()):
        try:
            answer = client.ask_question(dataset_id, question)
            st.success(answer["answer"])
            with st.expander("Supporting data"):
                st.json(answer.get("supporting_data", {}))
            with st.expander("Analyst plan"):
                st.json(answer.get("analyst", {}))
        except requests.RequestException as exc:
            st.warning(f"Could not answer question right now: {exc}")

    render_rag_section(client, dataset_id)


def render_rag_section(client: BackendClient, dataset_id: str) -> None:
    st.subheader("RAG Retrieval Preview")
    st.caption("Phase 1 indexes local dataset summaries, schema, profiles, generated insights, and limited sample rows. It retrieves chunks only and does not generate LLM answers yet.")

    try:
        status = client.get_rag_status(dataset_id)
    except requests.RequestException as exc:
        st.warning(f"Could not load RAG status: {exc}")
        return

    status_cols = st.columns(4)
    status_cols[0].metric("Index Status", status.get("status", "unknown"))
    status_cols[1].metric("Chunks", status.get("chunk_count", 0))
    status_cols[2].metric("Collection", status.get("collection", "analytics_chunks"))
    status_cols[3].metric("Indexed", "Yes" if status.get("indexed") else "No")
    if status.get("last_indexed_at"):
        st.caption(f"Last indexed: {status['last_indexed_at']}")

    control_cols = st.columns([1, 1, 2])
    rebuild = control_cols[0].checkbox("Rebuild", key=f"rag_rebuild_{dataset_id}")
    max_row_samples = control_cols[1].number_input("Row samples", min_value=0, max_value=100, value=20, step=5, key=f"rag_samples_{dataset_id}")
    if control_cols[2].button("Index dataset for retrieval", use_container_width=True):
        with st.spinner("Indexing dataset locally with ChromaDB..."):
            try:
                result = client.index_rag_dataset(dataset_id, rebuild=rebuild, max_row_samples=int(max_row_samples))
                st.success(result.get("message", "Dataset indexed."))
                st.json(result)
                st.rerun()
            except requests.RequestException as exc:
                st.warning(f"Could not index dataset: {exc}")

    delete_col, _ = st.columns([1, 3])
    if delete_col.button("Delete RAG index", use_container_width=True):
        try:
            result = client.delete_rag_index(dataset_id)
            st.info(result.get("message", "RAG index deleted."))
            st.rerun()
        except requests.RequestException as exc:
            st.warning(f"Could not delete RAG index: {exc}")

    query = st.text_input("Retrieve relevant chunks", placeholder="Example: Which columns explain revenue or churn?", key=f"rag_query_{dataset_id}")
    k = st.slider("Number of chunks", min_value=1, max_value=20, value=5, key=f"rag_k_{dataset_id}")
    if st.button("Retrieve chunks", disabled=not query.strip(), key=f"rag_retrieve_{dataset_id}"):
        try:
            payload = client.retrieve_rag(dataset_id, query=query, k=k)
            results = payload.get("results", [])
            if not results:
                st.info("No chunks returned. Index the dataset first or try a broader query.")
            for item in results:
                title = f"{item.get('chunk_type', 'chunk')} | {item.get('chunk_id', '')} | score {item.get('score', 0):.3f}"
                with st.expander(title, expanded=True):
                    st.write(item.get("text", "")[:1200])
                    st.caption(f"Distance: {item.get('distance')}")
                    st.json(item.get("metadata", {}))
        except requests.RequestException as exc:
            st.warning(f"Could not retrieve chunks: {exc}")


def render_visual_builder(client: BackendClient) -> None:
    st.header("Dashboard Studio")
    st.caption("Build Power BI/Tableau-style visuals using semantic field roles, safer defaults, and business-friendly settings.")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    try:
        schema = client.get_visual_builder_schema(dataset_id)
    except requests.RequestException as exc:
        st.warning(f"Could not load visual builder schema right now: {exc}")
        return

    dimensions = [field["name"] for field in schema.get("dimensions", [])]
    measures = [field["name"] for field in schema.get("measures", [])]
    semantic_fields = {field["name"]: field for field in schema.get("semantic_layer", [])}
    defaults = schema.get("suggested_defaults", {})
    storyboard_key = f"dashboard_studio_storyboard_{dataset_id}"
    selected_spec_key = f"dashboard_studio_spec_{dataset_id}"
    builder_mode_key = f"dashboard_studio_builder_mode_{dataset_id}"
    st.session_state.setdefault(storyboard_key, [])
    st.session_state.setdefault(builder_mode_key, "chart")

    if not dimensions:
        st.info("No business dimension fields are available for Dashboard Studio. Add category, region, date, product, or segment fields to build visuals.")
        return

    # Active toolbar with builder mode switching
    toolbar = st.columns(6)
    if toolbar[0].button("Add KPI", use_container_width=True, type="primary" if st.session_state[builder_mode_key] == "kpi" else "secondary"):
        st.session_state[builder_mode_key] = "kpi"
        st.rerun()
    if toolbar[1].button("Add Chart", use_container_width=True, type="primary" if st.session_state[builder_mode_key] == "chart" else "secondary"):
        st.session_state[builder_mode_key] = "chart"
        st.rerun()
    if toolbar[2].button("Add Table", use_container_width=True, type="primary" if st.session_state[builder_mode_key] == "table" else "secondary"):
        st.session_state[builder_mode_key] = "table"
        st.rerun()
    if toolbar[3].button("Add Slicer", use_container_width=True, type="primary" if st.session_state[builder_mode_key] == "slicer" else "secondary"):
        st.session_state[builder_mode_key] = "slicer"
        st.rerun()
    if toolbar[4].button("Add Insight", use_container_width=True, type="primary" if st.session_state[builder_mode_key] == "insight" else "secondary"):
        st.session_state[builder_mode_key] = "insight"
        st.rerun()
    has_spec = bool(st.session_state.get(selected_spec_key))
    if toolbar[5].button("Add to Storyboard", use_container_width=True, disabled=not has_spec):
        spec_item = st.session_state[selected_spec_key]
        st.session_state[storyboard_key].append(spec_item)
        st.success("Current visual added to storyboard for this session.")
    if not has_spec:
        st.caption("Create or select a visual before adding to Storyboard.")

    recommended_visuals = schema.get("recommended_visuals", [])
    if recommended_visuals:
        st.subheader("Recommended Visuals")
        for offset in range(0, min(len(recommended_visuals), 6), 3):
            rec_cols = st.columns(3)
            for col, recommendation in zip(rec_cols, recommended_visuals[offset : offset + 3]):
                with col.container(border=True):
                    st.markdown(f"**{recommendation.get('title', 'Recommended Visual')}**")
                    st.caption(recommendation.get("business_meaning", ""))
                    st.write(f"Chart: `{recommendation.get('suggested_chart_type', '')}`")
                    fields_used = ", ".join(recommendation.get("fields_used", [])) or "Dataset records"
                    st.write(f"Fields: {fields_used}")
                    st.caption(recommendation.get("why_useful", ""))
                    if recommendation.get("short_ai_insight"):
                        st.info(recommendation["short_ai_insight"])
                    action_cols = st.columns(2)
                    if action_cols[0].button("Use this Visual", key=f"use_{recommendation.get('visual_id')}", use_container_width=True):
                        st.session_state[selected_spec_key] = recommendation.get("spec", {})
                        st.session_state[builder_mode_key] = recommendation.get("spec", {}).get("chart_type", "chart") if recommendation.get("spec", {}).get("chart_type") != "kpi" else "chart"
                        st.rerun()
                    if action_cols[1].button("Add to Storyboard", key=f"story_{recommendation.get('visual_id')}", use_container_width=True):
                        st.session_state[storyboard_key].append(recommendation)
                        st.success("Added to storyboard for this session.")

    # Builder panels based on active mode
    builder_mode = st.session_state[builder_mode_key]
    if builder_mode == "kpi":
        with st.container(border=True):
            st.subheader("KPI Builder")
            st.caption("Configure a headline KPI metric for the dashboard.")
            kpi_measure = st.selectbox("KPI Metric", ["Count"] + measures, key=f"kpi_measure_{dataset_id}")
            kpi_label = st.text_input("KPI Label", value=kpi_measure if kpi_measure != "Count" else "Total Records", key=f"kpi_label_{dataset_id}")
            if st.button("Create KPI", key=f"create_kpi_{dataset_id}", use_container_width=True, type="primary"):
                kpi_spec = {
                    "chart_type": "table",
                    "dimension": dimensions[0] if dimensions else None,
                    "measure": None if kpi_measure == "Count" else kpi_measure,
                    "aggregation": "count" if kpi_measure == "Count" else "sum",
                    "sort": "descending",
                    "title": kpi_label,
                    "data_labels": True,
                    "filters": {},
                }
                st.session_state[selected_spec_key] = kpi_spec
                st.rerun()

    elif builder_mode == "table":
        with st.container(border=True):
            st.subheader("Table / Matrix Builder")
            st.caption("Configure a tabular view of your data.")
            table_dim = st.selectbox("Rows", dimensions, key=f"table_dim_{dataset_id}")
            table_meas = st.selectbox("Values", ["Count"] + measures, key=f"table_meas_{dataset_id}")
            table_agg = st.selectbox("Aggregation", ["sum", "mean", "count", "min", "max"], key=f"table_agg_{dataset_id}")
            if st.button("Create Table", key=f"create_table_{dataset_id}", use_container_width=True, type="primary"):
                table_spec = {
                    "chart_type": "table",
                    "dimension": table_dim,
                    "measure": None if table_meas == "Count" else table_meas,
                    "aggregation": table_agg,
                    "sort": "descending",
                    "title": f"{table_meas or 'Count'} by {table_dim}",
                    "data_labels": True,
                    "filters": {},
                }
                st.session_state[selected_spec_key] = table_spec
                st.rerun()

    elif builder_mode == "slicer":
        with st.container(border=True):
            st.subheader("Slicer Builder")
            st.caption("Add interactive filters to the dashboard canvas.")
            st.info("Slicers are configured in the Slicers panel below. Select fields to filter by.")
            slicer_fields = list(schema.get("filters", {}).keys())
            if slicer_fields:
                chosen = st.multiselect("Available filter fields", slicer_fields, key=f"slicer_fields_{dataset_id}")
                if chosen:
                    st.success(f"Slicers active for: {', '.join(chosen)}")
            else:
                st.info("No filter-eligible fields detected in the current dataset.")

    elif builder_mode == "insight":
        with st.container(border=True):
            st.subheader("Insight Card Builder")
            st.caption("Add an AI-generated insight card to the canvas.")
            try:
                insight_payload = client.get_insights(dataset_id)
                insights = insight_payload.get("insights", [])
                if insights:
                    chosen_insight = st.selectbox("Select insight", [i.get("title", i.get("message", "")) for i in insights], key=f"insight_sel_{dataset_id}")
                    if st.button("Add Insight to Canvas", key=f"add_insight_{dataset_id}", use_container_width=True, type="primary"):
                        matched = next((i for i in insights if i.get("title", i.get("message", "")) == chosen_insight), insights[0])
                        st.session_state[selected_spec_key] = {"insight": matched, "chart_type": "insight"}
                        st.rerun()
                else:
                    st.info("No AI insights are available for the current dataset.")
            except requests.RequestException:
                st.info("Could not load insights for insight card builder.")

    # Chart builder (always visible, active when builder_mode == "chart")
    filters = _dashboard_studio_slicer_payload(schema, dataset_id)
    canvas, settings = st.columns([2.2, 1])
    selected_spec = st.session_state.get(selected_spec_key, {})
    with settings:
        st.subheader("Visual Settings")
        selected_dimension_default = selected_spec.get("dimension") or defaults.get("dimension")
        dimension = st.selectbox(
            "Dimension / Axis",
            dimensions,
            index=dimensions.index(selected_dimension_default) if selected_dimension_default in dimensions else 0,
        )
        measure_options = ["Count"] + measures
        default_measure = selected_spec.get("measure") or (defaults.get("measure") if defaults.get("measure") in measures else "Count")
        default_measure = default_measure if default_measure in measure_options else "Count"
        measure_label = st.selectbox(
            "Measure / Value",
            measure_options,
            index=measure_options.index(default_measure) if default_measure in measure_options else 0,
        )
        chart_options = ["bar", "horizontal_bar", "line", "pie", "table"]
        default_chart = selected_spec.get("chart_type") or (defaults.get("chart_type") if defaults.get("chart_type") in chart_options else "bar")
        chart_type = st.selectbox("Chart Type", chart_options, index=chart_options.index(default_chart))
        aggregation_options = ["sum", "mean", "count", "min", "max"]
        default_aggregation = selected_spec.get("aggregation") or defaults.get("aggregation", "sum")
        aggregation = st.selectbox(
            "Aggregation",
            aggregation_options,
            index=aggregation_options.index(default_aggregation) if default_aggregation in aggregation_options else 0,
        )
        sort_options = ["descending", "ascending", "none"]
        default_sort = selected_spec.get("sort", "descending")
        sort = st.selectbox("Sort", sort_options, index=sort_options.index(default_sort) if default_sort in sort_options else 0)
        legend = st.selectbox("Legend", ["None"] + dimensions, index=0)
        tooltip = st.selectbox("Tooltip", ["Auto"] + dimensions + measures, index=0)
        number_formats = ["Auto", "Whole Number", "Decimal Number", "Currency", "Percentage"]
        default_number_format = selected_spec.get("number_format", "Auto")
        number_format = st.selectbox(
            "Number Format",
            number_formats,
            index=number_formats.index(default_number_format) if default_number_format in number_formats else 0,
        )
        title = st.text_input("Title", value=selected_spec.get("title") or "")
        data_labels = st.checkbox("Data Labels", value=bool(selected_spec.get("data_labels", True)))
        selected_dimension_meta = semantic_fields.get(dimension, {})
        selected_measure_meta = semantic_fields.get(measure_label, {}) if measure_label != "Count" else {}
        if selected_dimension_meta.get("helper_message"):
            st.warning(selected_dimension_meta["helper_message"])
        if selected_measure_meta.get("helper_message"):
            st.warning(selected_measure_meta["helper_message"])
        st.caption(
            f"Axis role: {selected_dimension_meta.get('semantic_role', 'unknown')} | "
            f"Measure role: {selected_measure_meta.get('semantic_role', 'count') if measure_label != 'Count' else 'count'}"
        )

    spec = {
        "chart_type": chart_type,
        "dimension": dimension,
        "measure": None if measure_label == "Count" else measure_label,
        "aggregation": aggregation,
        "sort": sort,
        "legend": None if legend == "None" else legend,
        "tooltip": None if tooltip == "Auto" else tooltip,
        "number_format": number_format,
        "title": title.strip() or None,
        "data_labels": data_labels,
        "filters": filters,
    }

    if builder_mode == "chart" or spec.get("chart_type") not in {"insight"}:
        try:
            visual = client.render_visual(dataset_id, spec)
        except requests.RequestException as exc:
            st.warning(f"Could not render visual right now: {exc}")
            return

        for warning in visual.get("semantic_warnings", []):
            st.warning(warning)

        with canvas:
            st.subheader("Dashboard Canvas")
            chart = visual.get("chart", {})
            plotly_spec = chart.get("plotly", {})
            fig = go.Figure(data=plotly_spec.get("data", []), layout=plotly_spec.get("layout", {}))
            with st.container(border=True):
                st.markdown(f"**{chart.get('title', 'Dashboard Visual')}**")
                st.caption(chart.get("metadata", {}).get("short_ai_insight", "Use this visual to compare business performance across the selected fields."))
                filtered_rows = chart.get("metadata", {}).get("filtered_rows")
                if filtered_rows == 0:
                    st.warning("No data matches the selected filters.")
                else:
                    st.plotly_chart(fig, use_container_width=True)
                card_cols = st.columns(3)
                if card_cols[0].button("Add to Storyboard", key="add_current_visual_storyboard", use_container_width=True):
                    st.session_state[storyboard_key].append(
                        {
                            "title": chart.get("title", "Dashboard Visual"),
                            "business_meaning": chart.get("metadata", {}).get("short_ai_insight", ""),
                            "suggested_chart_type": visual.get("applied_spec", {}).get("chart_type", ""),
                            "fields_used": chart.get("fields", []),
                            "spec": visual.get("applied_spec", {}),
                            "short_ai_insight": chart.get("metadata", {}).get("short_ai_insight", ""),
                        }
                    )
                    st.success("Current visual added to storyboard for this session.")
                card_cols[1].button("Export Visual", use_container_width=True, disabled=True)
                card_cols[2].caption("Export uses report exports in this MVP phase.")
            storyboard = st.session_state.get(storyboard_key, [])
            if storyboard:
                with st.expander(f"Storyboard ({len(storyboard)} visuals)", expanded=False):
                    for item in storyboard:
                        st.write(f"**{item.get('title')}**")
                        st.caption(item.get("business_meaning") or item.get("short_ai_insight", ""))
            with st.expander("Semantic Layer"):
                semantic_rows = [
                    {
                        "Column": field.get("name"),
                        "Role": field.get("semantic_role"),
                        "Type": field.get("semantic_type"),
                        "Unique Values": field.get("unique_count"),
                        "Priority": field.get("business_priority"),
                    }
                    for field in schema.get("semantic_layer", [])
                ]
                st.dataframe(pd.DataFrame(semantic_rows), use_container_width=True, hide_index=True)

        with st.expander("Suggestions"):
            st.dataframe(pd.DataFrame(visual.get("suggestions", [])), use_container_width=True)


def render_export_downloads(
    client: BackendClient,
    dataset_id: str,
    chart_ids: list[str] | None = None,
    package: str = "executive",
    label_prefix: str = "",
) -> None:
    def export_url(report_format: str) -> str:
        params: list[tuple[str, str]] = [("format", report_format), ("package", package)]
        for chart_id in chart_ids or []:
            params.append(("chart_ids", chart_id))
        return f"{client.base_url}/report/{dataset_id}/export?{urlencode(params)}"

    selected_count = len(chart_ids or [])
    target = "complete dashboard" if not chart_ids else f"{selected_count} selected visual{'s' if selected_count != 1 else ''}"
    st.markdown(f"**Download exports for {target}**")
    st.caption(
        "Click one format to generate and download it. Large PDF/PPTX exports may take a moment, but the page will not time out."
    )
    download_path = "C:\\Users\\DELL\\Downloads"
    file_names = {
        "JSON": f"{dataset_id}_report.json",
        "CSV": f"{dataset_id}.csv",
        "PDF": f"{dataset_id}_executive_report.pdf",
        "PPTX": f"{dataset_id}_executive_deck.pptx",
        "Excel": f"{dataset_id}_executive_report.xlsx",
        "PNG": f"{dataset_id}_dashboard_snapshot.png",
    }
    st.info(
        f"Download location: browser Downloads folder, usually `{download_path}` on this machine. "
        "If your browser asks where to save files, it will use the folder you choose."
    )
    with st.expander("Export file names"):
        for label, file_name in file_names.items():
            st.write(f"**{label}:** `{file_name}`")

    safe_prefix = f"{label_prefix} " if label_prefix else ""
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.link_button(
        f"{safe_prefix}JSON",
        export_url("json"),
        use_container_width=True,
    )
    col2.link_button(
        f"{safe_prefix}CSV",
        export_url("csv"),
        use_container_width=True,
    )
    col3.link_button(
        f"{safe_prefix}PDF",
        export_url("pdf"),
        use_container_width=True,
    )
    col4.link_button(
        f"{safe_prefix}PPTX",
        export_url("pptx"),
        use_container_width=True,
    )
    col5.link_button(
        f"{safe_prefix}Excel",
        export_url("xlsx"),
        use_container_width=True,
    )
    col6.link_button(
        f"{safe_prefix}PNG",
        export_url("png"),
        use_container_width=True,
    )


def render_reports(client: BackendClient) -> None:
    st.header("Reports")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    try:
        report = client.get_report(dataset_id)
    except requests.RequestException as exc:
        st.warning(f"Could not load report preview right now: {exc}")
        return

    branding = report.get("branding", {})
    if branding:
        st.caption(branding.get("company_name", ""))
        st.subheader(branding.get("report_title", "Executive Report"))

    overview = report.get("overview", {})
    cols = st.columns(3)
    cols[0].metric("Rows", f"{overview.get('row_count', 0):,}")
    cols[1].metric("Columns", f"{overview.get('column_count', 0):,}")
    cols[2].metric("Charts", f"{report.get('chart_count', 0):,}")

    guardrails = report.get("analysis_guardrails", {})
    if guardrails:
        with st.expander("Analysis Readiness", expanded=False):
            st.write(guardrails.get("summary", ""))
            readiness_cols = st.columns(4)
            supports = guardrails.get("supports", {})
            readiness_cols[0].metric("KPI", "Yes" if supports.get("kpi_tracking") else "No")
            readiness_cols[1].metric("Trend", "Yes" if supports.get("trend_analysis") else "No")
            readiness_cols[2].metric("Comparison", "Yes" if supports.get("comparison_analysis") else "No")
            readiness_cols[3].metric("Maps", "Yes" if supports.get("geographic_analysis") else "No")
            for item in guardrails.get("invalid_methods", []):
                st.warning(item)

    executive = report.get("executive_summary", {})
    if executive:
        st.subheader("Executive Summary")
        st.write(f"**Insight:** {executive.get('insight', '')}")
        st.write(f"**Reason:** {executive.get('reason', '')}")
        st.write(f"**Action:** {executive.get('action', '')}")

        business_story = report.get("business_story", {})
        if business_story:
            with st.expander("Business Storytelling Engine", expanded=True):
                st.write(f"**Data Story:** {business_story.get('data_story', '')}")
                st.write(f"**Trend Story:** {business_story.get('trend_story', '')}")
                st.write(f"**Business Story:** {business_story.get('business_story', '')}")

        tabs = st.tabs(["Action Framework", "Findings", "Risks", "Opportunities", "Recommendations", "Action Plan"])
        with tabs[0]:
            st.dataframe(safe_table(executive.get("decision_framework", [])), use_container_width=True)
        with tabs[1]:
            st.dataframe(safe_table(executive.get("key_findings", [])), use_container_width=True)
        with tabs[2]:
            risks = executive.get("risks", [])
            if risks:
                st.dataframe(safe_table(risks), use_container_width=True)
            else:
                st.success("No material risks detected from the current evidence.")
        with tabs[3]:
            st.dataframe(safe_table(executive.get("opportunities", [])), use_container_width=True)
        with tabs[4]:
            st.dataframe(safe_table(executive.get("recommendations", [])), use_container_width=True)
        with tabs[5]:
            st.dataframe(safe_table(executive.get("action_plan", [])), use_container_width=True)

    chart_specs = report.get("chart_specs", [])
    chart_labels = {f"{chart.get('title', chart.get('chart_id'))} ({chart.get('chart_type', 'chart')})": chart.get("chart_id") for chart in chart_specs}
    st.subheader("Export Package")
    package = st.selectbox(
        "Report package",
        ["executive", "board", "dashboard", "selected_visuals"],
        format_func=lambda value: {
            "executive": "Executive Report",
            "board": "Board Report",
            "dashboard": "Complete Dashboard",
            "selected_visuals": "Selected Visuals Only",
        }[value],
    )
    selected_labels = st.multiselect(
        "Visuals to include",
        list(chart_labels),
        default=list(chart_labels) if package != "selected_visuals" else list(chart_labels)[: min(3, len(chart_labels))],
    )
    selected_chart_ids = [chart_labels[label] for label in selected_labels if chart_labels.get(label)]
    if chart_specs:
        st.success(
            f"{len(selected_chart_ids)} visual(s) selected. Use the buttons below to download them as PDF, PPTX, PNG, JSON, or CSV."
        )
    else:
        st.info("No generated dashboard visuals are available for this dataset yet.")

    with st.container(border=True):
        render_export_downloads(
            client,
            dataset_id,
            selected_chart_ids,
            package,
            label_prefix="Download",
        )


def render_sql_lab(client: BackendClient) -> None:
    st.header("SQL Analytics Lab")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    try:
        templates = client.get_sql_templates(dataset_id).get("templates", [])
        history = client.get_sql_history(dataset_id)
    except requests.RequestException as exc:
        st.warning(f"Could not load SQL Lab right now: {exc}")
        return

    if "sql_lab_query" not in st.session_state:
        st.session_state["sql_lab_query"] = templates[0]["sql"] if templates else "SELECT * FROM dataset LIMIT 20"
    if "sql_lab_query_pending" in st.session_state:
        st.session_state["sql_lab_query"] = st.session_state.pop("sql_lab_query_pending")

    left, right = st.columns([2, 1])
    with right:
        st.subheader("Templates")
        for template in templates:
            if st.button(template["name"], key=f"template_{template['name']}", use_container_width=True):
                st.session_state["sql_lab_query"] = template["sql"]
                st.rerun()

        st.subheader("History")
        for item in reversed(history.get("history", [])[-5:]):
            if st.button(item["sql"][:48], key=f"history_{item.get('created_at')}", use_container_width=True):
                st.session_state["sql_lab_query"] = item["sql"]
                st.rerun()

        st.subheader("Saved")
        for item in history.get("saved_queries", [])[-8:]:
            if st.button(item["name"], key=f"saved_{item.get('created_at')}", use_container_width=True):
                st.session_state["sql_lab_query"] = item["sql"]
                st.rerun()

    with left:
        prompt = st.text_input("Generate SQL from natural language", placeholder="Show top 10 customers by revenue")
        if st.button("Generate SQL", disabled=not prompt.strip(), key=f"sql_generate_{dataset_id}"):
            try:
                generated = client.generate_sql(dataset_id, prompt)
                st.session_state["sql_lab_query_pending"] = generated["sql"]
                st.session_state["sql_lab_result"] = client.run_sql(dataset_id, generated["sql"], 100)
                st.session_state["sql_lab_message"] = generated.get("explanation", "")
                st.rerun()
            except requests.RequestException as exc:
                st.warning(f"Could not generate SQL right now: {exc}")

        sql = st.text_area("SQL editor", key="sql_lab_query", height=180)
        limit = st.slider("Preview limit", 10, 1000, 100, step=10)
        actions = st.columns(5)

        if actions[0].button("Run", type="primary", use_container_width=True, key=f"sql_run_{dataset_id}"):
            try:
                result = client.run_sql(dataset_id, sql, limit)
                st.session_state["sql_lab_result"] = result
            except requests.RequestException as exc:
                st.warning(f"SQL failed: {exc}")
        if actions[1].button("Explain", use_container_width=True, key=f"sql_explain_{dataset_id}"):
            try:
                st.info(client.explain_sql(sql).get("explanation", ""))
            except requests.RequestException as exc:
                st.warning(f"Could not explain SQL right now: {exc}")
        if actions[2].button("Optimize", use_container_width=True, key=f"sql_optimize_{dataset_id}"):
            try:
                optimized = client.optimize_sql(sql)
                st.session_state["sql_lab_query_pending"] = optimized["sql"]
                st.session_state["sql_lab_message"] = optimized.get("suggestions", "")
                st.rerun()
            except requests.RequestException as exc:
                st.warning(f"Could not optimize SQL right now: {exc}")
        if st.session_state.get("sql_lab_message"):
            st.info(st.session_state.pop("sql_lab_message"))
        if actions[3].button("Detect Errors", use_container_width=True, key=f"sql_detect_errors_{dataset_id}"):
            try:
                checked = client.detect_sql_errors(sql)
                st.success("No SQL safety issues detected.") if checked.get("valid") else st.warning(checked.get("error", "Invalid SQL"))
            except requests.RequestException as exc:
                st.warning(f"Could not detect SQL errors right now: {exc}")
        if actions[4].button("Save", use_container_width=True, key=f"sql_save_{dataset_id}"):
            try:
                client.save_sql(dataset_id, f"Query {len(history.get('saved_queries', [])) + 1}", sql)
                st.success("Query saved.")
            except requests.RequestException as exc:
                st.warning(f"Could not save query right now: {exc}")

        result = st.session_state.get("sql_lab_result")
        if result:
            st.subheader("Result Preview")
            result_df = pd.DataFrame(result.get("rows", []))
            st.dataframe(result_df, use_container_width=True)
            st.download_button(
                "Export results CSV",
                result_df.to_csv(index=False).encode("utf-8"),
                file_name=f"{dataset_id}_sql_results.csv",
                mime="text/csv",
            )


def _presentation_slides(report: dict) -> list[dict]:
    executive = report.get("executive_summary", {})
    story = report.get("business_story", {})
    kpis = report.get("kpi_cards", [])
    blocks = executive.get("decision_framework", [])
    return [
        {"title": "Executive Summary", "body": [executive.get("insight", ""), executive.get("reason", ""), executive.get("action", "")]},
        {"title": "Business Health Overview", "body": [story.get("business_story", "")]},
        {"title": "Key KPIs", "kpis": kpis[:4], "body": []},
        {"title": "Revenue Analysis", "body": [blocks[0].get("what_happened", "") if blocks else "", blocks[0].get("why_it_happened", "") if blocks else ""]},
        {"title": "Customer Analysis", "body": [blocks[1].get("what_happened", "") if len(blocks) > 1 else "Segment analysis appears when customer or segment fields are available."]},
        {"title": "Root Cause Analysis", "body": [block.get("why_it_happened", "") for block in blocks[:3]]},
        {"title": "Risks", "body": [item.get("risk", "") + ": " + item.get("why_it_matters", "") for item in executive.get("risks", [])] or ["No material risks detected from current evidence."]},
        {"title": "Opportunities", "body": [item.get("opportunity", "") + ": " + item.get("why", "") for item in executive.get("opportunities", [])]},
        {"title": "Recommendations", "body": [item.get("recommendation", "") for item in executive.get("recommendations", [])]},
        {"title": "Action Plan", "body": [item.get("action", "") for item in executive.get("action_plan", [])]},
    ]


def render_presentation_mode(client: BackendClient) -> None:
    st.header("Presentation Mode")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    try:
        report = client.get_report(dataset_id)
    except requests.RequestException as exc:
        st.warning(f"Could not load presentation right now: {exc}")
        return

    slides = _presentation_slides(report)
    index = st.slider("Slide", 1, len(slides), 1) - 1
    slide = slides[index]
    branding = report.get("branding", {})
    theme = report.get("theme", {})
    primary = branding.get("primary_color", theme.get("primary", "#0078D4"))

    st.markdown(
        f"""
        <style>
        .presentation-frame {{
            min-height: 620px;
            border-radius: 10px;
            padding: 38px 44px;
            background: {theme.get('surface', '#FFFFFF')};
            border: 1px solid {theme.get('border', '#D9E0EA')};
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.10);
        }}
        .presentation-title {{
            color: {primary};
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 8px;
        }}
        .presentation-subtitle {{
            color: {theme.get('muted_text', '#5F6B7A')};
            margin-bottom: 28px;
        }}
        .presentation-body {{
            color: {theme.get('text', '#1B1F23')};
            font-size: 1.05rem;
            line-height: 1.55;
            margin-bottom: 14px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="presentation-frame">', unsafe_allow_html=True)
    st.markdown(f'<div class="presentation-title">{slide["title"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="presentation-subtitle">{branding.get("company_name", "AI Analytics")} | Slide {index + 1} of {len(slides)}</div>', unsafe_allow_html=True)
    if slide.get("kpis"):
        _render_kpi_cards(slide["kpis"], theme)
    for item in slide.get("body", []):
        if item:
            st.markdown(f'<div class="presentation-body">{item}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("Download Presentation")
    chart_specs = report.get("chart_specs", [])
    chart_labels = {
        f"{chart.get('title', chart.get('chart_id'))} ({chart.get('chart_type', 'chart')})": chart.get("chart_id")
        for chart in chart_specs
    }
    selected_labels = st.multiselect(
        "Visuals to include in presentation exports",
        list(chart_labels),
        default=list(chart_labels),
        key="presentation_export_visuals",
    )
    selected_chart_ids = [chart_labels[label] for label in selected_labels if chart_labels.get(label)]
    with st.container(border=True):
        render_export_downloads(
            client,
            dataset_id,
            selected_chart_ids,
            "dashboard",
            label_prefix="Download",
        )


def render_regional_analytics(client: BackendClient, dataset_id: str | None = None) -> None:
    if dataset_id is None:
        dataset_id = select_dataset(client, key="regional_analytics_dataset")
        if not dataset_id:
            return
    try:
        regional = client.get_regional_intelligence(dataset_id)
    except requests.RequestException as exc:
        st.warning(f"Could not load regional analytics right now: {exc}")
        return
    if not regional.get("available"):
        st.info(regional.get("geo_detection", {}).get("message", "No geographic fields detected."))
        st.write("Recommended columns: country, state, province, region, city, territory, postal code, latitude, longitude.")
        return
    st.subheader("Regional KPIs")
    cols = st.columns(max(1, min(3, len(regional.get("regional_kpis", [])))))
    for col, kpi in zip(cols, regional.get("regional_kpis", [])):
        col.metric(kpi.get("label", "Region"), kpi.get("region", ""), kpi.get("value", ""))
    if regional.get("regional_rows"):
        st.subheader("Regional Performance")
        st.dataframe(pd.DataFrame(regional["regional_rows"]), use_container_width=True)
    st.subheader("Executive Regional Insights")
    for item in regional.get("regional_insights", []):
        with st.expander(item.get("title", "Regional Insight"), expanded=True):
            st.write(item.get("insight", ""))
            st.write(f"**Recommendation:** {item.get('recommendation', '')}")
            st.json(item.get("evidence", []))


def render_geographic_insights(client: BackendClient, dataset_id: str | None = None) -> None:
    if dataset_id is None:
        dataset_id = select_dataset(client, key="geographic_insights_dataset")
        if not dataset_id:
            return
    try:
        regional = client.get_regional_intelligence(dataset_id)
    except requests.RequestException as exc:
        st.warning(f"Could not load geographic insights right now: {exc}")
        return
    if not regional.get("available"):
        st.info(regional.get("geo_detection", {}).get("message", "No geographic fields detected."))
        st.write("Maps are hidden until location fields are available.")
        return
    charts = regional.get("map_charts", [])
    if not charts:
        st.info("Geographic columns were detected, but no map-ready visual could be generated from the available values.")
        return
    for chart in charts:
        fig = go.Figure(data=chart.get("plotly", {}).get("data", []), layout=chart.get("plotly", {}).get("layout", {}))
        st.plotly_chart(fig, use_container_width=True)


def render_dax_studio(client: BackendClient) -> None:
    st.header("DAX Analytics Studio")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return
    try:
        library = client.get_dax_library(dataset_id)
    except requests.RequestException as exc:
        st.warning(f"Could not load DAX Studio right now: {exc}")
        return
    if "dax_formula" not in st.session_state:
        measures = library.get("measures", [])
        st.session_state["dax_formula"] = measures[0]["dax"] if measures else "Record Count =\nCOUNTROWS('Dataset')"
    if "dax_formula_pending" in st.session_state:
        st.session_state["dax_formula"] = st.session_state.pop("dax_formula_pending")

    def measure_name_from_dax(dax_text: str) -> str:
        first_line = dax_text.strip().splitlines()[0] if dax_text.strip() else "Custom Measure"
        return first_line.split("=", 1)[0].strip() or "Custom Measure"

    def preview_dataframe() -> pd.DataFrame:
        active_df = st.session_state.get("active_dataframe")
        if active_df is not None:
            return active_df.copy()
        try:
            return pd.DataFrame(client.get_preview(dataset_id, rows=100).get("rows", []))
        except requests.RequestException:
            return pd.DataFrame()

    def numeric_metric_from_dax(dax_text: str, df: pd.DataFrame) -> str | None:
        lowered = dax_text.lower()
        numeric_columns = df.select_dtypes(include="number").columns.tolist()
        for column in numeric_columns:
            if f"[{column.lower()}]" in lowered or column.lower() in lowered:
                return column
        return numeric_columns[0] if numeric_columns else None

    def category_column(df: pd.DataFrame, metric: str | None) -> str | None:
        candidates = [column for column in df.columns if column != metric and not pd.api.types.is_numeric_dtype(df[column])]
        return candidates[0] if candidates else None

    def dax_preview_value(dax_text: str, df: pd.DataFrame, metric: str | None) -> float | int | str:
        lowered = dax_text.lower()
        if df.empty:
            return "No preview data"
        if "countrows" in lowered or metric is None:
            return int(len(df))
        series = pd.to_numeric(df[metric], errors="coerce")
        if "average" in lowered or "average(" in lowered:
            return round(float(series.mean()), 2)
        if "divide" in lowered or "rate" in lowered or "%" in lowered:
            denominator = max(len(df), 1)
            return round(float(series.sum()) / denominator, 4)
        return round(float(series.sum()), 2)

    def render_best_visual_preview(package: dict, dax_text: str) -> None:
        df = preview_dataframe()
        best_visual = (package.get("best_visual") or package.get("measure_preview", {}).get("recommended_visual") or "KPI Card").lower()
        metric = numeric_metric_from_dax(dax_text, df)
        value = dax_preview_value(dax_text, df, metric)
        measure_name = measure_name_from_dax(dax_text)
        palette = st.session_state.get("chart_palette", ["#0078D4", "#004E8C", "#00B7C3", "#F2C811"])

        st.subheader("Best Visual Preview")
        st.caption(package.get("best_visual") or package.get("measure_preview", {}).get("recommended_visual") or "KPI Card")
        if df.empty:
            st.info("Preview needs dataset rows. Upload/select a dataset to render the recommended visual.")
            return

        if "gauge" in best_visual or "rate" in dax_text.lower() or "divide" in dax_text.lower():
            numeric_value = float(value) if isinstance(value, (int, float)) else 0
            if numeric_value <= 1:
                numeric_value *= 100
            fig = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=numeric_value,
                    number={"suffix": "%"},
                    title={"text": measure_name},
                    gauge={"axis": {"range": [0, 100]}, "bar": {"color": palette[0]}},
                )
            )
            fig.update_layout(height=340, margin={"l": 24, "r": 24, "t": 48, "b": 24})
            st.plotly_chart(fig, use_container_width=True)
            return

        if "line" in best_visual or "trend" in best_visual or "ytd" in dax_text.lower() or "rolling" in dax_text.lower():
            if metric:
                series = pd.to_numeric(df[metric], errors="coerce").fillna(0).head(50).reset_index(drop=True)
                fig = go.Figure(data=[go.Scatter(x=list(range(1, len(series) + 1)), y=series, mode="lines+markers", line={"color": palette[0]})])
                fig.update_layout(title=measure_name, xaxis_title="Record Sequence", yaxis_title=metric, height=360)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.metric(measure_name, value)
            return

        category = category_column(df, metric)
        if category and metric and ("bar" in best_visual or "column" in best_visual or "comparison" in best_visual):
            grouped = df.groupby(category, dropna=False)[metric].sum().reset_index().sort_values(metric, ascending=False).head(12)
            grouped[category] = grouped[category].astype(str)
            fig = go.Figure(data=[go.Bar(x=grouped[category], y=grouped[metric], marker={"color": palette[: len(grouped)]})])
            fig.update_layout(title=measure_name, xaxis_title=category, yaxis_title=metric, height=380)
            fig.update_xaxes(automargin=True)
            st.plotly_chart(fig, use_container_width=True)
            return

        st.metric(measure_name, value)

    def package_from_editor(dax_text: str) -> dict:
        measure_name = measure_name_from_dax(dax_text)
        lowered = dax_text.lower()
        recommended = "Line Chart" if any(token in lowered for token in ["totalytd", "datesinperiod", "rolling"]) else "Gauge" if "divide" in lowered or "rate" in lowered else "KPI Card"
        return {
            "dax": dax_text,
            "dax_output": dax_text,
            "measure_preview": {
                "measure_name": measure_name,
                "preview_value": "",
                "recommended_visual": recommended,
                "preview_note": "Preview generated locally from the selected dataset.",
            },
            "best_visual": recommended,
            "business_meaning": "Custom DAX measure prepared for dashboard use.",
            "key_insight": "Use the preview to verify whether this measure belongs as a KPI, trend, or category comparison.",
            "next_best_question": "Which segment, period, or category should this measure be compared against?",
            "export_ready_summary": f"{measure_name} is ready to review and save as a custom DAX measure.",
        }

    def render_dax_package(package: dict) -> None:
        if not package:
            return
        st.subheader("Measure Preview")
        dax_text = package.get("dax_output") or package.get("dax_measure") or package.get("dax", "")
        if dax_text:
            st.code(dax_text, language="DAX")

        preview = package.get("measure_preview", {})
        if preview:
            preview_value = preview.get("preview_value", "")
            if preview_value:
                st.metric("Preview", preview_value)
            preview_row = {
                "Measure Name": preview.get("measure_name", ""),
                "Business Meaning": package.get("business_meaning") or package.get("pdf_ppt_business_interpretation", ""),
                "Metric Type": preview.get("metric_type") or preview.get("value_type", ""),
                "Data Type": preview.get("data_type", ""),
                "Display Format": preview.get("display_format") or preview.get("expected_format", ""),
                "Power BI Format String": "Open Advanced Format",
                "Recommended Visual": preview.get("recommended_visual") or package.get("best_visual", ""),
            }
            st.dataframe(pd.DataFrame([preview_row]), use_container_width=True, hide_index=True)
            st.caption(preview.get("preview_note", ""))
            with st.expander("Advanced Format"):
                st.write("Raw Power BI format string")
                st.code(preview.get("power_bi_format_string") or preview.get("expected_format", "") or "Not applicable")

        validation = package.get("data_logic_validation", {})
        if validation.get("invalid_reasons"):
            for item in validation.get("invalid_reasons", []):
                st.warning(item)

        st.subheader("Best Visual")
        st.info(package.get("best_visual") or (package.get("recommended_visual_types", ["KPI Card"])[0]))
        render_best_visual_preview(package, dax_text)

        st.subheader("Dashboard Placement")
        placement = package.get("dashboard_placement", {})
        st.write(f"**Page:** {placement.get('page', '')}")
        st.write(f"**Section:** {placement.get('section', '')}")
        st.write(f"**Purpose in flow:** {placement.get('purpose_in_flow', '')}")

        st.subheader("Business Interpretation")
        st.write(package.get("business_meaning") or package.get("pdf_ppt_business_interpretation", ""))

        st.subheader("Executive Insight")
        st.success(package.get("key_insight") or package.get("executive_insight_summary", ""))

        st.subheader("Next Best Analysis")
        st.write(package.get("next_best_question", ""))

        st.subheader("Export-Ready Summary")
        st.write(package.get("export_ready_summary", ""))

        with st.expander("Dashboard Integration Guidance"):
            for item in package.get("dashboard_integration_guidance", []):
                st.write(f"- {item}")

    left, right = st.columns([2, 1])
    with right:
        st.subheader("DAX Library")
        st.caption(f"Detected domain: {library.get('domain', 'Generic Analytics')}")
        custom_key = f"custom_dax_measures_{dataset_id}"
        st.session_state.setdefault(custom_key, [])
        custom_measures = st.session_state[custom_key]
        if custom_measures:
            st.markdown("**Custom Measures**")
            for index, measure in enumerate(custom_measures):
                if st.button(measure["name"], key=f"custom_dax_{dataset_id}_{index}", use_container_width=True):
                    st.session_state["dax_formula"] = measure["dax"]
                    st.session_state["dax_package"] = package_from_editor(measure["dax"])
                    st.rerun()
            st.divider()
        st.markdown("**Suggested Measures**")
        for measure in library.get("measures", []):
            if st.button(measure["name"], key=f"dax_{measure['name']}", use_container_width=True):
                st.session_state["dax_formula"] = measure["dax"]
                st.session_state["dax_package"] = package_from_editor(measure["dax"])
                st.rerun()

    with left:
        prompt = st.text_input("Generate DAX from natural language", placeholder="Create Revenue YTD")
        if st.button("Generate DAX", disabled=not prompt.strip(), key=f"dax_generate_{dataset_id}"):
            try:
                generated = client.generate_dax(dataset_id, prompt)
                st.session_state["dax_formula_pending"] = generated["dax"]
                st.session_state["dax_package"] = generated
                st.session_state["dax_message"] = generated.get("explanation", "")
                st.rerun()
            except requests.RequestException as exc:
                st.warning(f"Could not generate DAX right now: {exc}")
        measure_label = st.text_input("Custom measure name", value=measure_name_from_dax(st.session_state.get("dax_formula", "")), key=f"dax_measure_name_{dataset_id}")
        dax = st.text_area("Power BI measure builder", key="dax_formula", height=220)
        actions = st.columns(6)
        if actions[0].button("Explain", use_container_width=True, key=f"dax_explain_{dataset_id}"):
            try:
                st.info(client.explain_dax(dax).get("explanation", ""))
            except requests.RequestException as exc:
                st.warning(f"Could not explain DAX right now: {exc}")
        if actions[1].button("Optimize", use_container_width=True, key=f"dax_optimize_{dataset_id}"):
            try:
                optimized = client.optimize_dax(dax, dataset_id)
                st.session_state["dax_formula_pending"] = optimized["dax"]
                st.session_state["dax_package"] = optimized
                st.session_state["dax_message"] = optimized.get("suggestions", "")
                st.rerun()
            except requests.RequestException as exc:
                st.warning(f"Could not optimize DAX right now: {exc}")
        if st.session_state.get("dax_message"):
            st.info(st.session_state.pop("dax_message"))
        if actions[2].button("Detect Errors", use_container_width=True, key=f"dax_detect_errors_{dataset_id}"):
            try:
                checked = client.detect_dax_errors(dax)
                st.success("No DAX structure issues detected.") if checked.get("valid") else st.warning(checked.get("error", "Invalid DAX"))
            except requests.RequestException as exc:
                st.warning(f"Could not detect DAX errors right now: {exc}")
        if actions[3].button("Preview Visual", use_container_width=True, key=f"dax_preview_visual_{dataset_id}"):
            st.session_state["dax_package"] = package_from_editor(dax)
        if actions[4].button("Save Measure", use_container_width=True, key=f"dax_save_measure_{dataset_id}"):
            saved = {"name": measure_label.strip() or measure_name_from_dax(dax), "dax": dax}
            st.session_state[custom_key] = [item for item in st.session_state[custom_key] if item["name"] != saved["name"]]
            st.session_state[custom_key].append(saved)
            st.success(f"Saved custom DAX measure: {saved['name']}")
        if actions[5].button("Use as KPI", use_container_width=True, key=f"dax_use_as_kpi_{dataset_id}"):
            st.session_state["dax_package"] = {**package_from_editor(dax), "best_visual": "KPI Card"}
        render_dax_package(st.session_state.get("dax_package", {}))


def _build_storyboard_kpis(schema: dict) -> list[dict]:
    """Build simple KPI cards from visual builder schema metrics."""
    kpis = []
    row_count = 0
    semantic = schema.get("semantic_layer", [])
    measures = schema.get("measures", [])
    for field in semantic:
        if field.get("semantic_role") in {"revenue_currency_column"}:
            kpis.append({"label": f"Total {field['name']}", "value": "—", "icon": "chart"})
        elif field.get("semantic_role") in {"percentage_ratio_column"}:
            kpis.append({"label": field["name"].replace("_", " ").title(), "value": "—", "icon": "metric"})
    if not kpis:
        if measures:
            for m in measures[:2]:
                kpis.append({"label": m["name"].replace("_", " ").title(), "value": "—", "icon": "metric"})
        else:
            kpis.append({"label": "Records", "value": f"{row_count:,}" if row_count else "—", "icon": "table"})
    return kpis[:4]


def render_storyboard_builder(client: BackendClient) -> None:
    st.header("Storyboard Builder")
    st.caption("Turn Dashboard Studio visuals into a Tableau-style business story for executive review.")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    storyboard_key = f"dashboard_studio_storyboard_{dataset_id}"
    slide_key = f"storyboard_slide_{dataset_id}"
    visuals = st.session_state.get(storyboard_key, [])

    if not visuals:
        st.info("If no visuals are added yet, go to Dashboard Studio and click Add to Storyboard.")
        return

    try:
        schema = client.get_visual_builder_schema(dataset_id)
    except requests.RequestException:
        schema = {}

    template = st.selectbox(
        "Storyboard template",
        [
            "Executive Overview",
            "Sales Performance Story",
            "Customer Churn Story",
            "Inventory Health Story",
            "Financial Performance Story",
            "Marketing Performance Story",
            "General Business Review",
        ],
    )
    layout_mode = st.selectbox(
        "Slide layout",
        ["Visual + Summary", "Visual only", "Table only", "Summary only", "KPI + Chart", "Full Storyboard"],
    )
    include_options = st.multiselect(
        "Include sections",
        [
            "Executive Summary",
            "KPI Overview",
            "Trend Analysis",
            "Category Comparison",
            "Detailed Table",
            "Recommendations",
            "Risk Analysis",
            "Opportunity Analysis",
            "Location Insights",
        ],
        default=["Executive Summary", "KPI Overview", "Recommendations"],
    )

    slide_count = len(visuals)
    st.session_state.setdefault(slide_key, 0)
    st.session_state[slide_key] = min(st.session_state[slide_key], slide_count - 1)

    nav_left, nav_mid, nav_right = st.columns([1, 2, 1])
    if nav_left.button("Previous slide", use_container_width=True, disabled=st.session_state[slide_key] == 0):
        st.session_state[slide_key] -= 1
        st.rerun()
    selected_slide = nav_mid.selectbox(
        "Slide selector",
        list(range(1, slide_count + 1)),
        index=st.session_state[slide_key],
    )
    st.session_state[slide_key] = selected_slide - 1
    if nav_right.button("Next slide", use_container_width=True, disabled=st.session_state[slide_key] >= slide_count - 1):
        st.session_state[slide_key] += 1
        st.rerun()

    current = visuals[st.session_state[slide_key]]
    st.caption(f"Slide {st.session_state[slide_key] + 1} of {slide_count} | {template}")

    with st.container(border=True):
        st.subheader(current.get("title", "Storyboard Slide"))
        st.caption(" | ".join(include_options) if include_options else "No sections selected")

        storyboard_kpis = _build_storyboard_kpis(schema)
        if layout_mode in {"KPI + Chart", "Full Storyboard"}:
            kpi_cols = st.columns(min(len(storyboard_kpis), 4))
            for col, kpi in zip(kpi_cols, storyboard_kpis):
                col.metric(kpi["label"], kpi["value"])

        insight = current.get("short_ai_insight") or current.get("business_meaning", "")
        explanation = current.get("business_meaning") or "This slide summarizes the selected dashboard visual for business review."
        recommendation = current.get("why_useful") or "Use this slide to guide the next management discussion."

        spec = current.get("spec", {})
        if layout_mode not in {"Summary only", "Table only"} and spec.get("dimension"):
            try:
                visual = client.render_visual(dataset_id, spec)
                chart = visual.get("chart", {})
                plotly_spec = chart.get("plotly", {})
                st.plotly_chart(go.Figure(data=plotly_spec.get("data", []), layout=plotly_spec.get("layout", {})), use_container_width=True)
            except requests.RequestException as exc:
                st.warning(f"Could not render storyboard visual: {exc}")
        elif layout_mode == "Table only":
            st.dataframe(pd.DataFrame([current.get("spec", {})]), use_container_width=True)

        if layout_mode in {"Visual + Summary", "Summary only", "KPI + Chart", "Full Storyboard"}:
            summary_cols = st.columns(3)
            summary_cols[0].markdown("**AI Insight**")
            summary_cols[0].write(insight or "Insight will appear when more evidence is available.")
            summary_cols[1].markdown("**Business Explanation**")
            summary_cols[1].write(explanation)
            summary_cols[2].markdown("**Recommendation**")
            summary_cols[2].write(recommendation)
        st.caption(f"Page {st.session_state[slide_key] + 1} of {slide_count}")


def render_location_insights(client: BackendClient) -> None:
    st.header("Location Insights")
    st.caption("Regional analysis and map-based geographic views in one place.")
    dataset_id = select_dataset(client, key="location_insights_dataset_select")
    if not dataset_id:
        return
    regional_tab, map_tab = st.tabs(["Regional Analysis", "Map View"])
    with regional_tab:
        render_regional_analytics(client, dataset_id=dataset_id)
    with map_tab:
        render_geographic_insights(client, dataset_id=dataset_id)


def main() -> None:
    api_base_url = st.sidebar.text_input("Backend API URL", value=DEFAULT_API_BASE_URL)
    client = get_client(api_base_url)
    if "branding" not in st.session_state:
        initialize_session_state(get_active_branding(client))
    else:
        initialize_session_state()
    branding = st.session_state["branding"]

    st.title(branding.get("company_name", "AI Analytics SaaS MVP"))
    st.caption(branding.get("report_title", "Executive Decision Intelligence Report"))
    if branding.get("report_subtitle"):
        st.caption(branding["report_subtitle"])

    render_backend_status(client)
    render_theme_selector(client)
    render_branding_editor(client, branding)

    page = st.sidebar.radio(
        "Navigation",
        [
            "Dataset Preview",
            "Stats Dashboard",
            "AI Insights",
            "Dashboard Studio",
            "Reports",
            "SQL Lab",
            "DAX Studio",
            "Location Insights",
            "Storyboard Builder",
        ],
    )

    if page == "Dataset Preview":
        render_dataset_overview(client)
    elif page == "Stats Dashboard":
        render_dashboard(client)
    elif page == "AI Insights":
        render_ai_insights(client)
    elif page == "Dashboard Studio":
        render_visual_builder(client)
    elif page == "Reports":
        render_reports(client)
    elif page == "SQL Lab":
        render_sql_lab(client)
    elif page == "DAX Studio":
        render_dax_studio(client)
    elif page == "Location Insights":
        render_location_insights(client)
    elif page == "Storyboard Builder":
        render_storyboard_builder(client)

    if branding.get("footer_note"):
        st.caption(branding["footer_note"])


if __name__ == "__main__":
    main()

