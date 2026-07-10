from __future__ import annotations

import json
import re
from typing import Any


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _matches_type(value: Any, expected: str) -> bool:
    expected = str(expected or "").lower()
    actual = _type_name(value)
    if expected in {"", "any"}:
        return True
    if expected == "number":
        return actual in {"number", "integer"}
    if expected == "integer":
        return actual == "integer"
    if expected == "boolean":
        return actual == "boolean"
    if expected == "string":
        return actual == "string"
    if expected == "array":
        return actual == "array"
    if expected == "object":
        return actual == "object"
    if expected == "null":
        return actual == "null"
    return actual == expected


def validate_schema(
    data: Any,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate data against a lightweight JSON-schema-like dict."""
    issues: list[str] = []
    schema = schema or {"type": "object"}
    expected_type = schema.get("type", "object")

    if not _matches_type(data, str(expected_type)):
        issues.append(f"Expected type {expected_type}, got {_type_name(data)}")
        return {
            "valid": False,
            "issues": issues,
            "issue_count": len(issues),
            "data": data if isinstance(data, dict) else {},
        }

    if isinstance(data, dict) and expected_type == "object":
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        required = list(schema.get("required") or [])
        # If required not set, treat declared properties as soft-required for repair.
        for key in required:
            if key not in data:
                issues.append(f"Missing required field: {key}")
        for key, prop_schema in properties.items():
            if key not in data:
                continue
            if not isinstance(prop_schema, dict):
                continue
            prop_type = prop_schema.get("type")
            if prop_type and not _matches_type(data[key], str(prop_type)):
                issues.append(
                    f"Incorrect type for '{key}': expected {prop_type}, got {_type_name(data[key])}"
                )

    return {
        "valid": not issues,
        "issues": issues,
        "issue_count": len(issues),
        "data": data if isinstance(data, dict) else {"value": data},
    }


def _extract_json_blob(text: str) -> Any | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try fenced code block
    fence = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            pass
    # Try first {...} object
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            pass
    return None


def parse_structured_response(
    response: Any,
    *,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse provider output into structured data and validate against schema."""
    schema = schema or {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "insights": {"type": "array"},
            "recommendations": {"type": "array"},
        },
        "required": ["answer"],
    }
    raw_text = ""
    data: Any = None

    if isinstance(response, dict):
        if "data" in response and isinstance(response["data"], dict):
            data = response["data"]
        elif "structured_output" in response and isinstance(response["structured_output"], dict):
            data = response["structured_output"]
        elif any(k in response for k in ("answer", "summary", "insights", "recommendations")):
            data = response
        else:
            raw_text = str(response.get("text") or response.get("content") or "")
            data = _extract_json_blob(raw_text)
    elif isinstance(response, str):
        raw_text = response
        data = _extract_json_blob(response)
    else:
        raw_text = str(response)
        data = _extract_json_blob(raw_text)

    if data is None:
        repaired = repair_response(raw_text or response, schema=schema)
        return {
            "valid": repaired.get("valid", False),
            "issues": repaired.get("issues") or ["invalid JSON"],
            "issue_count": repaired.get("issue_count", 1),
            "data": repaired.get("data") or {},
            "repaired": True,
            "final_answer": repaired.get("final_answer", ""),
            "validation_status": "repaired" if repaired.get("valid") else "invalid",
        }

    validation = validate_schema(data, schema)
    if validation["valid"]:
        final_answer = ""
        if isinstance(data, dict):
            final_answer = str(data.get("answer") or data.get("summary") or data.get("content") or "")
        return {
            "valid": True,
            "issues": [],
            "issue_count": 0,
            "data": data if isinstance(data, dict) else {"value": data},
            "repaired": False,
            "final_answer": final_answer,
            "validation_status": "valid",
        }

    repaired = repair_response(data, schema=schema, issues=validation["issues"])
    return {
        "valid": repaired.get("valid", False),
        "issues": list(validation["issues"]) + list(repaired.get("issues") or []),
        "issue_count": len(list(validation["issues"]) + list(repaired.get("issues") or [])),
        "data": repaired.get("data") or {},
        "repaired": True,
        "final_answer": repaired.get("final_answer", ""),
        "validation_status": "repaired" if repaired.get("valid") else "invalid",
    }


def repair_response(
    response: Any,
    *,
    schema: dict[str, Any] | None = None,
    issues: list[str] | None = None,
) -> dict[str, Any]:
    """Best-effort repair for invalid JSON, missing fields, and incorrect types.

    Stores only final answer / structured result / validation status — no CoT.
    """
    schema = schema or {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "insights": {"type": "array"},
            "recommendations": {"type": "array"},
        },
        "required": ["answer"],
    }
    repair_notes = list(issues or [])
    data: dict[str, Any] = {}

    if isinstance(response, dict):
        data = dict(response)
    elif isinstance(response, str):
        parsed = _extract_json_blob(response)
        if isinstance(parsed, dict):
            data = dict(parsed)
        else:
            data = {"answer": response.strip()}
            repair_notes.append("Coerced free text into answer field")
    elif response is None:
        data = {}
        repair_notes.append("Empty response")
    else:
        data = {"answer": str(response)}
        repair_notes.append("Coerced non-dict response into answer field")

    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = list(schema.get("required") or [])

    for key, prop_schema in properties.items():
        if key in data:
            expected = str((prop_schema or {}).get("type") or "")
            if expected and not _matches_type(data[key], expected):
                # Type coercion
                if expected == "string":
                    data[key] = str(data[key])
                    repair_notes.append(f"Coerced '{key}' to string")
                elif expected == "array":
                    data[key] = [data[key]] if data[key] is not None else []
                    repair_notes.append(f"Coerced '{key}' to array")
                elif expected in {"number", "integer"}:
                    try:
                        data[key] = float(data[key]) if expected == "number" else int(data[key])
                        repair_notes.append(f"Coerced '{key}' to {expected}")
                    except Exception:
                        data[key] = 0 if expected == "integer" else 0.0
                        repair_notes.append(f"Reset '{key}' to default {expected}")
                elif expected == "object":
                    data[key] = {"value": data[key]}
                    repair_notes.append(f"Coerced '{key}' to object")
                elif expected == "boolean":
                    data[key] = bool(data[key])
                    repair_notes.append(f"Coerced '{key}' to boolean")
        else:
            # Fill missing with safe defaults
            expected = str((prop_schema or {}).get("type") or "string")
            defaults = {
                "string": "",
                "array": [],
                "object": {},
                "number": 0.0,
                "integer": 0,
                "boolean": False,
                "null": None,
            }
            if key in required or key in {"answer", "insights", "recommendations", "summary"}:
                data[key] = defaults.get(expected, "")
                repair_notes.append(f"Filled missing field '{key}'")

    for key in required:
        if key not in data:
            data[key] = "" if key in {"answer", "summary"} else ([] if key.endswith("s") else "")
            repair_notes.append(f"Filled required field '{key}'")

    # Prefer answer from summary if answer empty
    if not str(data.get("answer") or "").strip() and data.get("summary"):
        data["answer"] = str(data["summary"])
        repair_notes.append("Copied summary into answer")

    validation = validate_schema(data, schema)
    final_answer = str(data.get("answer") or data.get("summary") or data.get("content") or "")
    return {
        "valid": validation["valid"],
        "issues": repair_notes + list(validation.get("issues") or []),
        "issue_count": len(repair_notes) + int(validation.get("issue_count") or 0),
        "data": data,
        "final_answer": final_answer,
        "validation_status": "repaired" if validation["valid"] else "invalid",
        # Explicitly no chain-of-thought / hidden reasoning storage
        "stored_fields": ["final_answer", "structured_result", "validation_status"],
    }
