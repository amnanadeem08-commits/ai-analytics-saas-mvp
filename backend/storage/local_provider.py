from __future__ import annotations

"""Local filesystem storage provider (Sprint 8.4)."""

from pathlib import Path

from backend.storage.interfaces import StorageBackend


class LocalStorageProvider(StorageBackend):
    provider_name = "local"

    def __init__(self, root_dir: Path) -> None:
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = key.replace("\\", "/").lstrip("/")
        path = (self._root / safe).resolve()
        root = self._root.resolve()
        if not str(path).startswith(str(root)):
            raise ValueError("Invalid storage key path traversal detected.")
        return path

    def write(self, key: str, content: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def read(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(f"Storage key not found: {key}")
        return path.read_bytes()

    def delete(self, key: str) -> bool:
        path = self._path(key)
        if not path.exists():
            return False
        path.unlink()
        return True

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def list_keys(self, prefix: str = "") -> list[str]:
        base = self._root if not prefix else self._path(prefix)
        if not base.exists():
            return []
        keys: list[str] = []
        for path in base.rglob("*"):
            if path.is_file():
                rel = path.relative_to(self._root).as_posix()
                if not prefix or rel.startswith(prefix.rstrip("/")):
                    keys.append(rel)
        return sorted(keys)
