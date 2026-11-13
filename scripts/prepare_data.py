"""Create data/telco_churn.csv: tries the real IBM Telco dataset, falls back to the synthetic generator."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml import data as D  # noqa: E402

dest = ROOT / "data" / "telco_churn.csv"
dest.parent.mkdir(exist_ok=True)
if "--synthetic" not in sys.argv:
    try:
        df = D.download_telco(dest)
        print(f"Downloaded IBM Telco dataset: {len(df)} rows -> {dest}")
        raise SystemExit(0)
    except RuntimeError as exc:
        print(f"[info] {exc}\nFalling back to synthetic data.")
df = D.generate_synthetic(7043, seed=42)
df.to_csv(dest, index=False)
print(f"Generated synthetic dataset: {len(df)} rows -> {dest}")
