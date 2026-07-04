import pandas as pd

from frontend.services.domain_detection_service import detect_dataset_domain


def test_detect_dataset_domain_uses_columns_title_metadata_and_values():
    healthcare = detect_dataset_domain(
        df=pd.DataFrame({"heart_rate": [80, 95], "glucose": [110, 120], "status": ["normal", "abnormal"]}),
        metadata={"description": "patient diagnosis monitoring"},
        title="clinic_health.csv",
    )
    assert healthcare["domain"] == "Healthcare"
    assert healthcare["confidence_score"] > 0
    assert "glucose" in healthcare["signals"]

    retail = detect_dataset_domain(
        columns=["sku", "store_id", "basket_value"],
        metadata={"semantic_layer": [{"name": "sku", "meaning": "product sold in store"}]},
        title="retail_checkout.csv",
    )
    assert retail["domain"] == "Retail"
    assert retail["confidence_score"] > 0

    manufacturing = detect_dataset_domain(
        df=pd.DataFrame({"batch": ["A1", "B2"], "machine_status": ["passed", "defective"]}),
        metadata={"source": "factory quality log"},
        title="plant_production.csv",
    )
    assert manufacturing["domain"] == "Manufacturing"
    assert manufacturing["confidence_score"] > 0


def test_detect_dataset_domain_falls_back_to_general():
    result = detect_dataset_domain(columns=["name", "value", "notes"], title="generic_upload.csv")
    assert result["domain"] == "Generic Business Dataset"
    assert result["confidence_score"] == 0.0



def test_detect_dataset_domain_distinguishes_churn_sales_and_hr():
    churn = detect_dataset_domain(columns=["customer_id", "churn", "tenure", "contract_type", "monthly_charges"])
    assert churn["domain"] == "Customer Churn"

    sales = detect_dataset_domain(columns=["order_date", "revenue", "sales", "product", "region"])
    assert sales["domain"] == "Sales"

    hr = detect_dataset_domain(columns=["employee_id", "department", "salary", "attrition", "hire_date"])
    assert hr["domain"] == "HR"
