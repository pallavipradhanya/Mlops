from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import yaml
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models import Dataset
from app.ml import data as D
from app.services import activity


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def try_dvc_add(path: Path) -> tuple[str | None, bool]:
    """Best-effort `dvc add`. Returns (md5, tracked). Never pretends: (None, False) if DVC is unavailable."""
    if os.getenv("MLOPS360_SKIP_DVC") or not shutil.which("dvc") or not (settings.root / ".dvc").exists():
        return None, False
    try:
        subprocess.run(["dvc", "add", str(path)], cwd=settings.root, check=True, capture_output=True, timeout=120)
        meta = yaml.safe_load(Path(str(path) + ".dvc").read_text())
        return meta["outs"][0]["md5"], True
    except Exception:  # noqa: BLE001
        return None, False


def register_file(db: Session, path: Path, name: str, source: str) -> tuple[Dataset, bool]:
    """Validate + register a CSV as a new dataset version. Returns (dataset, created)."""
    content = path.read_bytes()
    digest = sha256_bytes(content)
    existing = db.query(Dataset).filter(Dataset.sha256 == digest).first()
    if existing:
        return existing, False
    raw = pd.read_csv(path)
    df = D.clean_dataframe(raw)
    missing = D.missing_columns(df)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")
    if len(df) < 200:
        raise ValueError(f"Need at least 200 labeled rows, got {len(df)}")
    version = db.query(Dataset).filter(Dataset.name == name).count() + 1
    md5, tracked = try_dvc_add(path)
    ds = Dataset(
        name=name, version=version, path=str(path), sha256=digest, rows=len(df), columns=raw.shape[1],
        churn_rate=float(df[D.TARGET].mean()), source=source, dvc_md5=md5, dvc_tracked=tracked,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    activity.log(db, "dataset.registered", f"Dataset '{name}' v{version} registered ({len(df)} rows, source={source})")
    return ds, True


def save_upload(db: Session, filename: str, content: bytes, name: str | None = None) -> tuple[Dataset, bool]:
    stem = (name or Path(filename).stem).strip() or "dataset"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
    path = settings.uploads_dir / f"{safe}_{sha256_bytes(content)[:10]}.csv"
    path.write_bytes(content)
    try:
        return register_file(db, path, stem, "upload")
    except Exception:
        path.unlink(missing_ok=True)
        raise


def generate(db: Session, rows: int, seed: int, drift: bool, name: str | None) -> tuple[Dataset, bool]:
    df = D.generate_synthetic(n=rows, seed=seed, drift=drift)
    label = name or ("synthetic-drifted" if drift else "synthetic-telco")
    path = settings.uploads_dir / f"{label}_n{rows}_s{seed}.csv"
    df.to_csv(path, index=False)
    return register_file(db, path, label, "synthetic")


def fetch_ibm(db: Session) -> tuple[Dataset, bool]:
    path = settings.uploads_dir / "ibm_telco_churn.csv"
    D.download_telco(path)
    return register_file(db, path, "ibm-telco-churn", "ibm-telco")


def load(dataset: Dataset) -> pd.DataFrame:
    return D.clean_dataframe(pd.read_csv(dataset.path))


def latest(db: Session) -> Dataset | None:
    return db.query(Dataset).order_by(Dataset.id.desc()).first()
