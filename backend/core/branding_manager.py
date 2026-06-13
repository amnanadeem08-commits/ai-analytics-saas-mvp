from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from backend.core.config import settings


HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass
class OrganizationBranding:
    company_name: str = "AI Analytics"
    report_title: str = "Executive Decision Intelligence Report"
    logo_url: str = ""
    logo_path: str = ""
    primary_color: str = "#118DFF"
    secondary_color: str = "#12239E"
    accent_color: str = "#E66C37"
    theme_name: str = "power_bi_professional"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BrandingManager:
    """Local-first organization branding registry for dashboards and exports."""

    def _path(self) -> Path:
        return settings.BRANDING_FILE

    def _asset_dir(self) -> Path:
        return settings.BRAND_ASSETS_DIR

    def get(self) -> OrganizationBranding:
        path = self._path()
        if not path.exists():
            return OrganizationBranding()
        try:
            payload = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            payload = {}
        defaults = OrganizationBranding().to_dict()
        defaults.update({key: value for key, value in payload.items() if value is not None})
        return OrganizationBranding(**defaults)

    def update(self, payload: dict[str, Any]) -> OrganizationBranding:
        current = self.get().to_dict()
        allowed = set(current)
        for key, value in payload.items():
            if key in allowed and value is not None:
                current[key] = str(value).strip()

        for key in ["primary_color", "secondary_color", "accent_color"]:
            if not HEX_COLOR.match(current[key]):
                raise ValueError(f"{key} must be a hex color like #118DFF")

        branding = OrganizationBranding(**current)
        self._path().parent.mkdir(parents=True, exist_ok=True)
        self._path().write_text(json.dumps(branding.to_dict(), indent=2), encoding="utf-8")
        return branding

    def save_logo(self, filename: str, content: bytes) -> OrganizationBranding:
        suffix = Path(filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
            raise ValueError("Logo must be png, jpg, jpeg, webp, or svg.")
        if not content:
            raise ValueError("Logo file is empty.")

        asset_dir = self._asset_dir()
        asset_dir.mkdir(parents=True, exist_ok=True)
        logo_path = asset_dir / f"logo{suffix}"
        logo_path.write_bytes(content)

        return self.update(
            {
                "logo_path": str(logo_path),
                "logo_url": "/branding/logo/current",
            }
        )


branding_manager = BrandingManager()
