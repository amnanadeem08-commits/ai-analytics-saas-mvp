from pathlib import Path

import pandas as pd

from backend.core.config import settings


def save_uploaded_file(content: bytes, stored_filename: str) -> Path:
    path = settings.UPLOADS_DIR / stored_filename
    path.write_bytes(content)
    return path


def save_processed_dataframe(df: pd.DataFrame, processed_filename: str) -> Path:
    path = settings.PROCESSED_DIR / processed_filename
    df.to_csv(path, index=False)
    return path


def load_processed_dataframe(processed_filename: str) -> pd.DataFrame:
    path = settings.PROCESSED_DIR / processed_filename
    return pd.read_csv(path)
