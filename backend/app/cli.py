"""CLI used by DVC (`dvc repro`) and for scripted runs.

  python -m app.cli train --data ../data/telco_churn.csv
"""
from __future__ import annotations

import argparse
import json

from app.core.config import settings
from app.database.db import SessionLocal, init_db
from app.services import dataset_service, registry_service
from app.services.training_service import train_candidates


def main() -> None:
    parser = argparse.ArgumentParser("mlops360")
    sub = parser.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--data", required=True)
    t.add_argument("--metrics-out", default=str(settings.reports_dir / "metrics.json"))
    args = parser.parse_args()
    init_db()
    db = SessionLocal()
    try:
        from pathlib import Path
        ds, _ = dataset_service.register_file(db, Path(args.data).resolve(), Path(args.data).stem, "upload")
        dvc_file = Path(str(Path(args.data).resolve()) + ".dvc")
        if dvc_file.exists() and not ds.dvc_tracked:  # data was versioned with `dvc add`
            import yaml
            ds.dvc_md5, ds.dvc_tracked = yaml.safe_load(dvc_file.read_text())["outs"][0]["md5"], True
            db.commit()
        res = train_candidates(db, ds, trigger="dvc")
        stage = registry_service.stage_candidate(db, res["version"])
        out = {"version": res["version"], "stage": stage, "best": res["best"]["algorithm"],
               **{r["algorithm"]: r["metrics"] for r in res["results"]}}
        Path(args.metrics_out).write_text(json.dumps(out, indent=2))
        print(json.dumps(out, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
