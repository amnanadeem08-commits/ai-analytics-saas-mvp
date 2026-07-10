from __future__ import annotations

from backend.services.output_validation_service import (
    parse_structured_response,
    repair_response,
    validate_schema,
)

SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "insights": {"type": "array"},
        "recommendations": {"type": "array"},
    },
    "required": ["answer", "insights", "recommendations"],
}


def test_validate_schema_ok():
    data = {
        "answer": "Revenue declined in North",
        "insights": ["North down 12%"],
        "recommendations": ["Investigate North"],
    }
    result = validate_schema(data, SCHEMA)
    assert result["valid"] is True


def test_validate_schema_missing_and_wrong_types():
    result = validate_schema({"answer": 123, "insights": "x"}, SCHEMA)
    assert result["valid"] is False
    assert result["issue_count"] >= 1


def test_parse_invalid_json_repairs():
    parsed = parse_structured_response("not json at all — revenue fell", schema=SCHEMA)
    assert parsed["repaired"] is True
    assert isinstance(parsed["data"], dict)
    assert parsed["data"].get("answer")
    assert "validation_status" in parsed
    # No hidden reasoning keys
    assert "chain_of_thought" not in parsed
    assert "reasoning" not in parsed.get("data", {})


def test_parse_json_blob_from_text():
    text = 'Here you go:\n{"answer": "ok", "insights": ["a"], "recommendations": ["b"]}\n'
    parsed = parse_structured_response(text, schema=SCHEMA)
    assert parsed["valid"] is True or parsed["repaired"] is True
    assert parsed["data"]["answer"] == "ok"


def test_repair_missing_fields():
    repaired = repair_response({"answer": "done"}, schema=SCHEMA)
    assert "insights" in repaired["data"]
    assert "recommendations" in repaired["data"]
    assert repaired["final_answer"] == "done"
    assert set(repaired["stored_fields"]) == {
        "final_answer",
        "structured_result",
        "validation_status",
    }


def test_repair_incorrect_types():
    repaired = repair_response(
        {"answer": 42, "insights": "single", "recommendations": None},
        schema=SCHEMA,
    )
    assert isinstance(repaired["data"]["answer"], str)
    assert isinstance(repaired["data"]["insights"], list)
    assert isinstance(repaired["data"]["recommendations"], list)
