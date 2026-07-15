from __future__ import annotations

"""Theme injection — CSS variables + base component chrome for Streamlit."""

import streamlit as st

from frontend.design_system.tokens import css_root_vars


def inject_design_system_css() -> None:
    """Idempotent global design-system styles."""
    if st.session_state.get("_ds_css_injected"):
        return
    st.markdown(
        f"""
        <style>
        :root {{
            {css_root_vars()}
        }}
        html, body, [class*="css"] {{
            font-family: var(--ds-font-sans);
        }}
        .ds-display {{
            font-size: var(--ds-display-size); font-weight: 800; line-height: 1.2;
            color: var(--ds-text); letter-spacing: -0.02em; margin: 0 0 var(--ds-space-sm);
        }}
        .ds-heading {{
            font-size: var(--ds-heading-size); font-weight: 800; line-height: 1.3;
            color: var(--ds-text); margin: var(--ds-space-section) 0 var(--ds-space-xs);
        }}
        .ds-subheading {{
            font-size: var(--ds-subheading-size); font-weight: 700; color: var(--ds-text);
            margin: var(--ds-space-md) 0 var(--ds-space-xxs);
        }}
        .ds-body {{ font-size: var(--ds-body-size); color: var(--ds-text); line-height: 1.5; }}
        .ds-caption {{ font-size: var(--ds-caption-size); color: var(--ds-muted); margin: 0 0 var(--ds-space-sm); }}
        .ds-code {{
            font-family: var(--ds-font-mono); font-size: 0.85rem;
            background: var(--ds-primary-muted); padding: 0.1rem 0.35rem; border-radius: var(--ds-radius-sm);
        }}
        .ds-metric-value {{
            font-size: var(--ds-metric-size); font-weight: 800; color: var(--ds-primary); line-height: 1.2;
        }}
        .ds-card {{
            background: var(--ds-surface);
            border: 1px solid var(--ds-border);
            border-radius: var(--ds-radius-md);
            padding: var(--ds-space-md);
            margin: var(--ds-space-sm) 0;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
        }}
        .ds-card-section {{
            border-top: 3px solid var(--ds-primary);
        }}
        .ds-kpi {{
            background: var(--ds-surface);
            border: 1px solid color-mix(in srgb, var(--ds-primary) 22%, var(--ds-border));
            border-radius: var(--ds-radius-md);
            padding: var(--ds-space-sm) var(--ds-space-md);
            margin: var(--ds-space-xs) 0;
        }}
        .ds-kpi-label {{
            font-size: var(--ds-caption-size); font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.04em; color: var(--ds-muted);
        }}
        .ds-badge, .ds-tag, .ds-chip {{
            display: inline-block; padding: 0.15rem 0.55rem; border-radius: var(--ds-radius-pill);
            font-size: 0.75rem; font-weight: 700; color: #fff; letter-spacing: 0.02em;
        }}
        .ds-tag {{
            background: var(--ds-primary-muted); color: var(--ds-primary); border: 1px solid color-mix(in srgb, var(--ds-primary) 30%, transparent);
        }}
        .ds-alert {{
            border-radius: var(--ds-radius-md); padding: var(--ds-space-sm) var(--ds-space-md);
            margin: var(--ds-space-sm) 0; border: 1px solid var(--ds-border);
        }}
        .ds-alert-success {{ background: #ECFDF5; border-color: var(--ds-success); color: #14532D; }}
        .ds-alert-warning {{ background: #FFFBEB; border-color: var(--ds-warning); color: #78350F; }}
        .ds-alert-danger {{ background: #FEF2F2; border-color: var(--ds-danger); color: #7F1D1D; }}
        .ds-alert-info {{ background: #F0F9FF; border-color: var(--ds-info); color: #0C4A6E; }}
        .ds-search {{
            border: 1px solid var(--ds-border); border-radius: var(--ds-radius-md);
            padding: var(--ds-space-xs) var(--ds-space-sm); background: var(--ds-surface);
        }}
        .ds-page {{
            max-width: 1200px; margin: 0 auto; padding: 0 var(--ds-space-page-gutter, 0.5rem);
        }}
        .ds-stack-sm > * + * {{ margin-top: var(--ds-space-sm); }}
        .ds-stack-md > * + * {{ margin-top: var(--ds-space-md); }}
        /* Streamlit primary button alignment */
        div.stButton > button[kind="primary"] {{
            background: var(--ds-primary) !important;
            border-color: var(--ds-primary) !important;
        }}
        div[data-testid="stMetricValue"] {{ color: var(--ds-primary); }}
        @media (max-width: 700px) {{
            .ds-display {{ font-size: 1.5rem; }}
            .ds-heading {{ font-size: 1.15rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["_ds_css_injected"] = True


def apply_design_system() -> None:
    """Call once from app main() after session init."""
    inject_design_system_css()
