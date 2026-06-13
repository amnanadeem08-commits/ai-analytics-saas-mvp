from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "data" / "samples" / "sample_sales_data.csv"
target = ROOT / "data" / "uploads" / "sample_sales_data.csv"
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(source, target)
print(f"Copied sample data to {target}")
