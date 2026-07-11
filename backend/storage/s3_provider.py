from __future__ import annotations

"""S3 / S3-compatible object storage provider (Post-1.0 #3).

Uses boto3 with the standard credential chain. Supports custom endpoints
(MinIO, LocalStack) via S3_ENDPOINT.
"""

import logging
from typing import Any

from backend.storage.interfaces import StorageBackend

_log = logging.getLogger("ai_analytics.storage.s3")


class S3NotConfiguredError(RuntimeError):
    """Raised when S3 is selected but cannot be used."""


class S3StorageProvider(StorageBackend):
    provider_name = "s3"

    def __init__(
        self,
        *,
        bucket: str,
        endpoint: str = "",
        region: str = "us-east-1",
        client: Any | None = None,
    ) -> None:
        self._bucket = (bucket or "").strip()
        self._endpoint = (endpoint or "").strip()
        self._region = region or "us-east-1"
        if not self._bucket:
            raise S3NotConfiguredError(
                "S3 storage selected but S3_BUCKET is not configured. "
                "Set OBJECT_STORAGE_BACKEND=local or configure S3_BUCKET."
            )
        if client is not None:
            self._client = client
        else:
            self._client = self._build_client()

    def _build_client(self) -> Any:
        try:
            import boto3
            from botocore.config import Config as BotoConfig
        except ImportError as exc:
            raise S3NotConfiguredError(
                "boto3 is required for S3 storage. Install with: pip install boto3"
            ) from exc

        kwargs: dict[str, Any] = {
            "service_name": "s3",
            "region_name": self._region,
            "config": BotoConfig(signature_version="s3v4"),
        }
        if self._endpoint:
            kwargs["endpoint_url"] = self._endpoint
        return boto3.client(**kwargs)

    def write(self, key: str, content: bytes) -> None:
        safe = key.replace("\\", "/").lstrip("/")
        self._client.put_object(Bucket=self._bucket, Key=safe, Body=content)

    def read(self, key: str) -> bytes:
        safe = key.replace("\\", "/").lstrip("/")
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=safe)
        except Exception as exc:
            if self._is_not_found(exc):
                raise FileNotFoundError(f"Storage key not found: {key}") from exc
            raise
        body = response["Body"].read()
        return body if isinstance(body, (bytes, bytearray)) else bytes(body)

    def delete(self, key: str) -> bool:
        safe = key.replace("\\", "/").lstrip("/")
        if not self.exists(safe):
            return False
        self._client.delete_object(Bucket=self._bucket, Key=safe)
        return True

    def exists(self, key: str) -> bool:
        safe = key.replace("\\", "/").lstrip("/")
        try:
            self._client.head_object(Bucket=self._bucket, Key=safe)
            return True
        except Exception as exc:
            if self._is_not_found(exc):
                return False
            raise

    def list_keys(self, prefix: str = "") -> list[str]:
        safe_prefix = prefix.replace("\\", "/").lstrip("/")
        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=safe_prefix):
            for item in page.get("Contents") or []:
                key = item.get("Key")
                if key:
                    keys.append(str(key))
        return sorted(keys)

    @staticmethod
    def _is_not_found(exc: Exception) -> bool:
        response = getattr(exc, "response", None) or {}
        error = response.get("Error") or {}
        code = str(error.get("Code") or getattr(exc, "response", {}).get("Error", {}).get("Code") or "")
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        return code in {"404", "NoSuchKey", "NotFound", "404 Not Found"} or status == 404
