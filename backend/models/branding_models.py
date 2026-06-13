from typing import Any

from pydantic import BaseModel


class BrandingUpdate(BaseModel):
    company_name: str | None = None
    report_title: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    theme_name: str | None = None


class BrandingResponse(BaseModel):
    company_name: str
    report_title: str
    logo_url: str = ""
    logo_path: str = ""
    primary_color: str
    secondary_color: str
    accent_color: str
    theme_name: str


class BrandingPayload(BaseModel):
    branding: dict[str, Any]
