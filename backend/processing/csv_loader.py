from pathlib import Path

import pandas as pd

from backend.core.exceptions import FileValidationError


ENCODINGS_TO_TRY = ["utf-8", "utf-8-sig", "latin1"]


def load_csv(file_path: Path) -> pd.DataFrame:
    """Load CSV with a few common encoding fallbacks."""
    last_error: Exception | None = None

    for encoding in ENCODINGS_TO_TRY:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            if df.empty:
                raise FileValidationError("CSV file has no data rows.")
            return df
        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.EmptyDataError as exc:
            raise FileValidationError("CSV file is empty or invalid.") from exc
        except pd.errors.ParserError as exc:
            raise FileValidationError("CSV file could not be parsed. Please check the format.") from exc

    raise FileValidationError("CSV encoding is not supported.") from last_error
