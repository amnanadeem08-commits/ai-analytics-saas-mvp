from pathlib import Path
import os


class Settings:
    """Central application settings for local-first MVP."""

    APP_NAME: str = os.getenv("APP_NAME", "AI Analytics SaaS MVP")
    API_VERSION: str = os.getenv("API_VERSION", "1.0.0")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "200"))

    ROOT_DIR: Path = Path(__file__).resolve().parents[2]
    DATA_DIR: Path = ROOT_DIR / "data"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    METADATA_DIR: Path = DATA_DIR / "metadata"
    DATASETS_DIR: Path = DATA_DIR / "datasets"
    SAMPLES_DIR: Path = DATA_DIR / "samples"
    BRAND_ASSETS_DIR: Path = DATA_DIR / "branding"
    DATASETS_METADATA_FILE: Path = METADATA_DIR / "datasets.json"
    BRANDING_FILE: Path = METADATA_DIR / "branding.json"
    SQL_QUERIES_FILE: Path = METADATA_DIR / "sql_queries.json"
    THEME_STATE_FILE: Path = METADATA_DIR / "theme_state.json"

    ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xlsm"}

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()


def ensure_data_directories() -> None:
    """Create required local storage directories on app startup."""
    for directory in [
        settings.DATA_DIR,
        settings.UPLOADS_DIR,
        settings.PROCESSED_DIR,
        settings.METADATA_DIR,
        settings.DATASETS_DIR,
        settings.SAMPLES_DIR,
        settings.BRAND_ASSETS_DIR,
        settings.DATA_DIR / "storage",
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    if not settings.DATASETS_METADATA_FILE.exists():
        settings.DATASETS_METADATA_FILE.write_text("[]", encoding="utf-8")
    if not settings.BRANDING_FILE.exists():
        settings.BRANDING_FILE.write_text("{}", encoding="utf-8")
    if not settings.SQL_QUERIES_FILE.exists():
        settings.SQL_QUERIES_FILE.write_text("[]", encoding="utf-8")
    if not settings.THEME_STATE_FILE.exists():
        settings.THEME_STATE_FILE.write_text('{"active_theme": "power_bi_professional"}', encoding="utf-8")
