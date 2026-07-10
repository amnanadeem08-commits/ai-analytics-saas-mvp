import pandas as pd
import pytest

from frontend.services.business_columns_service import (
    RECIPE_REGISTRY,
    BusinessColumnRecipe,
    create_business_columns,
    detect_available_recipes,
    generate_domain_business_questions,
    generate_preview_rows,
    recipe_by_target,
)


def _base_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sales": [10, 20, 30],
            "quantity": [2, 3, 4],
            "cost": [5, 8, 9],
            "revenue": [10, 20, 30],  # also allow margin/profit relationships
            "profit": [1, 2, 3],
            "age": [10, 18, 60],
            "risk_score": [0.1, 0.5, 0.9],
            "requirements": ["reqA", "reqB", "reqC"],
        }
    )


def test_recipe_registry_targets_unique():
    targets = [r.target_column for r in RECIPE_REGISTRY]
    assert len(targets) == len(set(targets))


def test_detect_available_recipes_suggests_expected_targets():
    df = _base_df()
    suggestions = detect_available_recipes(df)
    targets = {s["target_column"] for s in suggestions}
    assert "Revenue" in targets
    assert "Profit" in targets
    assert "Margin %" in targets
    assert "Age Group" in targets
    assert "Risk Category" in targets
    assert "Requirements" in targets


def test_detect_available_recipes_does_not_suggest_existing_target():
    df = _base_df()
    df["Revenue"] = [999, 999, 999]  # existing calculated target
    suggestions = detect_available_recipes(df)
    targets = {s["target_column"] for s in suggestions}
    assert "Revenue" not in targets


def test_detect_available_recipes_missing_dependency_excludes_recipe():
    df = _base_df().drop(columns=["quantity"])
    suggestions = detect_available_recipes(df)
    targets = {s["target_column"] for s in suggestions}
    assert "Revenue" not in targets
    # other recipes should still be possible based on their own deps
    assert "Profit" in targets
    assert "Margin %" in targets


def test_detect_available_recipes_ranks_by_domain_context():
    df = _base_df()

    suggestions = detect_available_recipes(df, domain_context={"domain": "Sales"})
    ordered_targets = [item["target_column"] for item in suggestions]

    assert ordered_targets[:3] == ["Revenue", "Profit", "Margin %"]
    assert suggestions[0]["domain_context"] == "sales"
    assert "sales context" in suggestions[0]["description"].lower()


def test_customer_churn_domain_prioritizes_churn_business_columns():
    df = pd.DataFrame(
        {
            "customer_id": ["C1", "C2", "C3", "C4"],
            "churn": ["Yes", "No", "Yes", "No"],
            "tenure": [2, 12, 3, 24],
            "monthly_charges": [95, 40, 88, 55],
            "contract_type": ["Month-to-month", "Two year", "Month-to-month", "One year"],
            "payment_method": ["Electronic check", "Bank transfer", "Electronic check", "Mailed check"],
            "age": [21, 49, 35, 58],
        }
    )

    suggestions = detect_available_recipes(df, domain_context={"domain": "Customer Churn"})
    ordered = [item["target_column"] for item in suggestions]

    assert ordered[0] == "Churn Risk"
    assert "Customer Segment" in ordered[:4]
    assert "Revenue Band" in ordered[:5]
    assert ordered.index("Age Group") > ordered.index("Payment Risk")


def test_customer_churn_suggests_payment_risk_without_payment_method_column():
    df = pd.DataFrame(
        {
            "customer_id": ["C1", "C2", "C3"],
            "churn": ["Yes", "No", "Yes"],
            "tenure": [3, 18, 7],
            "monthly_charges": [91, 42, 85],
            "contract_type": ["Month-to-month", "One year", "Month-to-month"],
        }
    )

    suggestions = detect_available_recipes(df, domain_context={"domain": "Customer Churn"})
    ordered = [item["target_column"] for item in suggestions]

    assert "Payment Risk" in ordered


def test_customer_churn_suggests_payment_risk_with_payment_method_only():
    df = pd.DataFrame(
        {
            "customer_id": ["C1", "C2", "C3"],
            "churn": ["Yes", "No", "Yes"],
            "tenure": [3, 18, 7],
            "monthly_charges": [91, 42, 85],
            "payment_method": ["Electronic check", "Bank transfer", "Credit card"],
        }
    )

    suggestions = detect_available_recipes(df, domain_context={"domain": "Customer Churn"})
    ordered = [item["target_column"] for item in suggestions]

    assert "Payment Risk" in ordered


def test_customer_churn_suggests_contract_category_with_contract_alias():
    df = pd.DataFrame(
        {
            "customer_id": ["C1", "C2", "C3"],
            "churn": ["Yes", "No", "Yes"],
            "tenure": [3, 18, 7],
            "monthly_charges": [91, 42, 85],
            "contract": ["Month-to-month", "One year", "Two year"],
        }
    )

    suggestions = detect_available_recipes(df, domain_context={"domain": "Customer Churn"})
    ordered = [item["target_column"] for item in suggestions]

    assert "Contract Category" in ordered
    assert "Payment Risk" in ordered


def test_generate_domain_business_questions_for_churn():
    questions = generate_domain_business_questions({"domain": "Customer Churn"})

    assert questions
    assert any("churn risk" in q.lower() for q in questions)
    assert any("retention" in q.lower() or "loyalty" in q.lower() for q in questions)


def test_recipe_by_target_works():
    r = recipe_by_target("margin %")
    assert isinstance(r, BusinessColumnRecipe)
    assert r.target_column == "Margin %"
    assert recipe_by_target("does not exist") is None


def test_generate_preview_rows_revenue_formula_correct():
    df = pd.DataFrame({"sales": [1, 2], "quantity": [10, 20]})
    recipe = recipe_by_target("Revenue")
    assert recipe is not None

    preview = generate_preview_rows(df, recipe, preview_rows=2)
    assert preview == [{"Revenue": 10}, {"Revenue": 40}]


def test_generate_preview_rows_profit_formula_correct():
    df = pd.DataFrame({"revenue": [50, 40], "cost": [5, 10]})
    recipe = recipe_by_target("Profit")
    assert recipe is not None

    preview = generate_preview_rows(df, recipe, preview_rows=2)
    assert preview == [{"Profit": 45}, {"Profit": 30}]


def test_generate_preview_rows_margin_pct_formula_correct():
    df = pd.DataFrame({"revenue": [100, 200], "profit": [10, 20]})
    recipe = recipe_by_target("Margin %")
    assert recipe is not None

    preview = generate_preview_rows(df, recipe, preview_rows=2)
    # Profit / Revenue * 100 => 10%, 10%
    assert preview[0]["Margin %"] == pytest.approx(10.0)
    assert preview[1]["Margin %"] == pytest.approx(10.0)


def test_generate_preview_rows_age_group_formula_correct():
    df = pd.DataFrame({"age": [10, 18, 55]})
    recipe = recipe_by_target("Age Group")
    assert recipe is not None

    preview = generate_preview_rows(df, recipe, preview_rows=3)
    assert [row["Age Group"] for row in preview] == ["<18", "18-24", "55+"]


def test_generate_preview_rows_risk_category_formula_correct():
    df = pd.DataFrame({"risk_score": [0.1, 0.5, 0.9]})
    recipe = recipe_by_target("Risk Category")
    assert recipe is not None

    preview = generate_preview_rows(df, recipe, preview_rows=3)
    assert [row["Risk Category"] for row in preview] == ["Low", "Medium", "High"]


def test_generate_preview_rows_requirements_formula_correct():
    df = pd.DataFrame({"requirements_list": ["a", "b"]})
    recipe = recipe_by_target("Requirements")
    assert recipe is not None

    preview = generate_preview_rows(df, recipe, preview_rows=2)
    assert preview == [{"Requirements": "a"}, {"Requirements": "b"}]


def test_create_business_columns_does_not_mutate_original_df():
    df = _base_df()
    original = df.copy(deep=True)

    recipes = [
        recipe_by_target("Revenue"),
        recipe_by_target("Age Group"),
    ]
    recipes = [r for r in recipes if r is not None]

    new_df = create_business_columns(df, recipes)
    # original unchanged
    pd.testing.assert_frame_equal(df, original)
    # new df has new columns
    assert "Revenue" in new_df.columns
    assert "Age Group" in new_df.columns


def test_create_business_columns_does_not_overwrite_existing_target():
    df = _base_df()
    df["Revenue"] = [999, 999, 999]

    recipe = recipe_by_target("Revenue")
    assert recipe is not None
    new_df = create_business_columns(df, [recipe])

    # should keep existing values
    assert new_df["Revenue"].tolist() == [999, 999, 999]


def test_create_business_columns_empty_if_no_valid_recipes():
    df = _base_df()
    # Pick recipe with missing deps by creating a df that doesn't contain required inputs
    df2 = pd.DataFrame({"sales": [1, 2]})  # missing quantity => Revenue recipe should still not be applied
    recipe = recipe_by_target("Revenue")
    assert recipe is not None

    # create_business_columns will try formula; in expected usage, you should only pass recipes from detect.
    # Our test ensures we can pass an empty list and that it returns a copy.
    new_df = create_business_columns(df2, [])
    pd.testing.assert_frame_equal(new_df, df2)
