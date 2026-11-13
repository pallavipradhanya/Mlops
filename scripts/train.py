"""Entry point used by `dvc repro` (works from the repo root)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("MLOPS_HOME", str(ROOT))
os.environ["MLOPS360_SKIP_DVC"] = "1"  # DVC already holds its lock while running this stage

from app.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.argv.insert(1, "train")
    main()
