from __future__ import annotations

"""Streaming download helpers (Sprint 8.7)."""

from collections.abc import Iterator

from starlette.responses import StreamingResponse


def stream_bytes(chunks: Iterator[bytes], *, media_type: str = "application/octet-stream", filename: str = "") -> StreamingResponse:
    headers = {}
    if filename:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return StreamingResponse(chunks, media_type=media_type, headers=headers)


def chunk_file(content: bytes, *, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
    for i in range(0, len(content), chunk_size):
        yield content[i : i + chunk_size]
