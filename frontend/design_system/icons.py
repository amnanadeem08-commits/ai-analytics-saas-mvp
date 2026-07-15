from __future__ import annotations

"""Icon name map — Material icon names used by Streamlit sidebar / labels.

Keep semantic aliases stable; pages should prefer these keys over raw strings.
"""

ICONS: dict[str, str] = {
    "home": ":material/home:",
    "upload": ":material/upload_file:",
    "dataset": ":material/table_chart:",
    "clean": ":material/cleaning_services:",
    "analyze": ":material/analytics:",
    "chart": ":material/bar_chart:",
    "ai": ":material/psychology:",
    "workflow": ":material/play_circle:",
    "job": ":material/work_history:",
    "storage": ":material/folder:",
    "share": ":material/ios_share:",
    "settings": ":material/settings:",
    "account": ":material/person:",
    "admin": ":material/admin_panel_settings:",
    "search": ":material/search:",
    "success": ":material/check_circle:",
    "warning": ":material/warning:",
    "error": ":material/error:",
    "info": ":material/info:",
    "refresh": ":material/refresh:",
}


def icon(name: str, fallback: str = ":material/circle:") -> str:
    return ICONS.get(name, fallback)
