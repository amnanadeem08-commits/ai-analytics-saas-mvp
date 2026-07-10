from __future__ import annotations

"""S3 storage provider — interface + stub (Sprint 8.4).

Full S3 integration belongs to a later sprint. The stub validates configuration
and raises a clear error when invoked.
"""

from backend.storage.interfaces import StorageBackend


class S3NotConfiguredError(RuntimeError):
    pass


class S3StorageProvider(StorageBackend):
    provider_name = "s3"

    def __init__(self, *, bucket: str, endpoint: str = "", region: str = "us-east-1") -> None:
        self._bucket = bucket
        self._endpoint = endpoint
        self._region = region
        if not bucket:
            raise S3NotConfiguredError(
                "S3 storage selected but S3_BUCKET is not configured. "
                "Set STORAGE_BACKEND=local or configure S3_BUCKET."
            )

    def _stub(self, operation: str) -> None:
        raise S3NotConfiguredError(
            f"S3 {operation} is not implemented in this MVP sprint. "
            "Use STORAGE_BACKEND=local or wait for a future cloud sprint."
        )

    def write(self, key: str, content: bytes) -> None:
        _ = key, content
        self._stub("write")

    def read(self, key: str) -> bytes:
        _ = key
        self._stub("read")
        return b""

    def delete(self, key: str) -> bool:
        _ = key
        self._stub("delete")
        return False

    def exists(self, key: str) -> bool:
        _ = key
        self._stub("exists")
        return False

    def list_keys(self, prefix: str = "") -> list[str]:
        _ = prefix
        self._stub("list_keys")
        return []
