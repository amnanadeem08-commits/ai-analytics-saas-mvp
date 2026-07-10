from __future__ import annotations

"""Response compression helpers (Sprint 8.7)."""

import gzip
from typing import Any

from fastapi import Response


def gzip_json_response(payload: bytes, *, status_code: int = 200) -> Response:
    compressed = gzip.compress(payload)
    return Response(
        content=compressed,
        status_code=status_code,
        media_type="application/json",
        headers={"Content-Encoding": "gzip", "Vary": "Accept-Encoding"},
    )


def should_compress(accept_encoding: str | None, min_bytes: int, body_size: int) -> bool:
    if not accept_encoding or "gzip" not in accept_encoding.lower():
        return False
    return body_size >= min_bytes
