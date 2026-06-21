from frontend.components.storyboard_session import add_storyboard_entry


def test_add_storyboard_entry_sets_sequence_and_prevents_duplicate_chart_id():
    storyboard: list[dict] = []
    studio_chart_entry = {
        "chart_id": "visual_builder_horizontal_bar_region_sales",
        "title": "Sales by Region",
        "suggested_chart_type": "horizontal_bar",
        "spec": {
            "chart_type": "horizontal_bar",
            "dimension": "region",
            "measure": "sales",
        },
    }

    first_add = add_storyboard_entry(storyboard, studio_chart_entry)
    assert first_add["added"] is True
    assert len(storyboard) == 1
    assert storyboard[0]["chart_id"] == studio_chart_entry["chart_id"]
    assert storyboard[0]["sequence"] == 1
    assert storyboard[0]["order"] == 1

    second_add = add_storyboard_entry(storyboard, studio_chart_entry)
    assert second_add["added"] is False
    assert len(storyboard) == 1
    assert storyboard[0]["sequence"] == 1
    assert storyboard[0]["order"] == 1
