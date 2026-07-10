from __future__ import annotations

"""Input sanitization (Sprint 8.7)."""

import html
import re
from typing import Any

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SCRIPT_TAGS = re.compile(r"<\s*/?\s*script[^>]*>", re.IGNORECASE)


def sanitize_string(value: str, *, max_length: int = 10_000) -> str:
    text = value[:max_length]
    text = _CONTROL_CHARS.sub("", text)
    text = _SCRIPT_TAGS.sub("", text)
    return text.strip()


def sanitize_dict(data: dict[str, Any], *, max_length: int = 10_000) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            out[key] = sanitize_string(value, max_length=max_length)
        elif isinstance(value, dict):
            out[key] = sanitize_dict(value, max_length=max_length)
        elif isinstance(value, list):
            out[key] = [
                sanitize_string(v, max_length=max_length) if isinstance(v, str) else v for v in value
            ]
        else:
            out[key] = value
    return out


def escape_output(value: str) -> str:
    return html.escape(value, quote=True)
