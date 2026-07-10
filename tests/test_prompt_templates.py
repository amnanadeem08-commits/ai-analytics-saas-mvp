from backend.ai.prompt_templates import (
    BUSINESS_ANALYST_PROMPT,
    FINANCE_ANALYST_PROMPT,
    GENERAL_ANALYST_PROMPT,
    HEALTH_ANALYST_PROMPT,
    build_dataset_insight_prompt,
    detect_prompt_domain,
    select_analyst_prompt,
)


def test_prompt_domain_selection_matches_dataset_columns():
    assert detect_prompt_domain(["heart_rate", "blood_pressure", "glucose", "bmi"]) == "health"
    assert select_analyst_prompt(["diagnosis", "insulin"]) == HEALTH_ANALYST_PROMPT

    assert detect_prompt_domain(["revenue", "customer_id", "churn_flag"]) == "business"
    assert select_analyst_prompt(["sales", "profit"]) == BUSINESS_ANALYST_PROMPT

    assert detect_prompt_domain(["stock_price", "market_volume"]) == "finance"
    assert select_analyst_prompt(["stock", "price", "volume"]) == FINANCE_ANALYST_PROMPT

    assert detect_prompt_domain(["name", "category", "value"]) == "general"
    assert select_analyst_prompt(["name", "category", "value"]) == GENERAL_ANALYST_PROMPT


def test_build_dataset_insight_prompt_includes_selected_system_prompt():
    prompt = build_dataset_insight_prompt("Rows: 10", "What matters?", ["bmi", "glucose"])
    assert HEALTH_ANALYST_PROMPT in prompt
    assert "Rows: 10" in prompt
    assert "What matters?" in prompt
