import pandas as pd

from frontend.app_pages.storyboard_page import build_default_storyboard


def test_default_storyboard_generates_only_complete_chart_backed_slides():
    df = pd.DataFrame(
        {
            "region": ["North", "South", "East", "West"],
            "segment": ["Consumer", "Corporate", "Consumer", "Corporate"],
            "sales": [100, 150, 90, 130],
            "profit": [25, 40, 20, 35],
        }
    )

    slides = build_default_storyboard(df, "local_test_dataset", None, {})

    assert slides
    for slide in slides:
        assert slide.get("title")
        assert slide.get("insights")
        assert slide.get("kpis")
        assert slide.get("recommendations")
        assert slide.get("charts")
        assert slide["charts"][0].get("plotly", {}).get("data")
        assert "placeholder" not in str(slide).lower()
