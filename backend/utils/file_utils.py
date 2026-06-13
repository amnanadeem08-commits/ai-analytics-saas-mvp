from pathlib import Path
import re


def safe_filename(filename: str) -> str:
    """Return a filesystem-safe filename while keeping it readable."""
    name = Path(filename).name.strip()
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name or "dataset.csv"


def file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()
