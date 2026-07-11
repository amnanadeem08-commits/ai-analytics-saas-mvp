"""Shared helpers for PIOS CLIs (stdlib only)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PIOS = ROOT / "pios"
MANIFEST_PATH = PIOS / "MANIFEST.yaml"


def repo_root() -> Path:
    return ROOT


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML subset parser for MANIFEST.yaml (no PyYAML dependency)."""
    data: dict[str, Any] = {"dependency_rules": [], "keyword_module_map": {}, "doc_update_hints": {}, "packages": {}}
    current_list: list[Any] | None = None
    current_map: dict[str, Any] | None = None
    current_map_key: str | None = None
    current_rule: dict[str, Any] | None = None
    section: str | None = None
    package_name: str | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = line.strip()

        if indent == 0 and stripped.endswith(":") and not stripped.startswith("-"):
            key = stripped[:-1]
            section = key
            current_list = None
            current_map = None
            current_rule = None
            package_name = None
            if key == "dependency_rules":
                current_list = data["dependency_rules"]
            elif key in ("keyword_module_map", "doc_update_hints", "packages"):
                current_map = data[key]
            continue

        if section == "dependency_rules" and stripped.startswith("- "):
            current_rule = {}
            data["dependency_rules"].append(current_rule)
            rest = stripped[2:]
            if ":" in rest:
                k, v = rest.split(":", 1)
                current_rule[k.strip()] = _scalar(v.strip())
            continue

        if current_rule is not None and indent >= 2 and ":" in stripped and not stripped.startswith("-"):
            k, v = stripped.split(":", 1)
            current_rule[k.strip()] = _scalar(v.strip())
            continue

        if section in ("keyword_module_map", "doc_update_hints") and current_map is not None:
            if indent == 2 and ":" in stripped:
                k, v = stripped.split(":", 1)
                current_map_key = k.strip()
                v = v.strip()
                if v.startswith("[") and v.endswith("]"):
                    current_map[current_map_key] = _parse_list(v)
                elif v == "":
                    current_map[current_map_key] = []
                else:
                    current_map[current_map_key] = _scalar(v)
            continue

        if section == "packages" and current_map is not None:
            if indent == 2 and stripped.endswith(":"):
                package_name = stripped[:-1]
                current_map[package_name] = []
                continue
            if indent >= 4 and stripped.startswith("- ") and package_name:
                current_map[package_name].append(stripped[2:].strip())
            continue

        if indent == 0 and ":" in stripped and not stripped.startswith("-"):
            k, v = stripped.split(":", 1)
            data[k.strip()] = _scalar(v.strip())

    return data


def _scalar(value: str) -> Any:
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _parse_list(value: str) -> list[str]:
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [item.strip().strip("'\"") for item in inner.split(",")]


def load_manifest() -> dict[str, Any]:
    return parse_simple_yaml(read_text(MANIFEST_PATH))


def get_api_version() -> str:
    config = ROOT / "backend" / "core" / "config.py"
    text = read_text(config)
    match = re.search(r'API_VERSION:\s*str\s*=\s*os\.getenv\("API_VERSION",\s*"([^"]+)"\)', text)
    return match.group(1) if match else "unknown"


def count_files(pattern: str, base: Path) -> int:
    return sum(1 for _ in base.rglob(pattern) if _.is_file())


def list_route_modules() -> list[str]:
    routes = ROOT / "backend" / "api" / "routes"
    if not routes.exists():
        return []
    return sorted(p.name for p in routes.glob("*.py") if p.name != "__init__.py")


def git_output(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return (result.stdout or "").strip()
    except OSError:
        return ""
