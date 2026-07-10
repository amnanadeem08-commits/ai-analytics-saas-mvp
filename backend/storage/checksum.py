from __future__ import annotations

import hashlib

from backend.models.storage_models import FileChecksum


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def build_checksum(content: bytes) -> FileChecksum:
    return FileChecksum(algorithm="sha256", value=compute_sha256(content), size_bytes=len(content))


def verify(content: bytes, checksum: FileChecksum) -> bool:
    if not checksum or not checksum.value:
        return False
    if checksum.algorithm != "sha256":
        return False
    return hashlib.sha256(content).hexdigest() == checksum.value and len(content) == checksum.size_bytes
