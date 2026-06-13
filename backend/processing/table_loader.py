from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.core.exceptions import FileValidationError
from backend.processing.csv_loader import load_csv


EXCEL_EXTENSIONS = {".xlsx", ".xlsm"}


def load_table(file_path: Path) -> pd.DataFrame:
    """Load supported tabular upload formats into a dataframe."""
    extension = file_path.suffix.lower()
    if extension == ".csv":
        return load_csv(file_path)

    if extension in EXCEL_EXTENSIONS:
        try:
            df = pd.read_excel(file_path, engine="openpyxl")
        except ValueError as exc:
            raise FileValidationError("Excel file could not be parsed. Please check the workbook.") from exc
        except ImportError as exc:
            raise FileValidationError("Excel support requires openpyxl to be installed.") from exc

        if df.empty:
            raise FileValidationError("Excel file has no data rows.")
        return df

    raise FileValidationError("Unsupported file type.")
