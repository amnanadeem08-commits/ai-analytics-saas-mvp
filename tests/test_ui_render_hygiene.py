from pathlib import Path


FRONTEND_FILES = [
    "frontend/components/executive_storyboard.py",
    "frontend/app_pages/storyboard_page.py",
    "frontend/app_pages/dashboard_page.py",
    "frontend/app_pages/reports_page.py",
    "frontend/app_pages/location_page.py",
    "frontend/app_pages/ai_insights_page.py",
]


DISALLOWED_PATTERNS = [
    "st.markdown(\"</div>\",",
    "st.markdown('</div>',",
    "st.markdown(\"</section>\",",
    "st.markdown('</section>',",
    "st.json(",
]


def test_storyboard_and_dashboard_views_do_not_emit_raw_markup_or_json_dumps():
    for relative_path in FRONTEND_FILES:
        content = Path(relative_path).read_text(encoding="utf-8")
        for pattern in DISALLOWED_PATTERNS:
            assert pattern not in content, f"Found disallowed UI leakage pattern '{pattern}' in {relative_path}"
