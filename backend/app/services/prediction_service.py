from __future__ import annotations

import math

import pandas as pd
from sqlalchemy.orm import Session

from app.database.models import Prediction
from app.ml import data as D
from app.services import mlflow_service, registry_service


class NoModelError(RuntimeError):
    pass


def _clean_value(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def predict_rows(db: Session, rows: list[dict]) -> dict:
    version = registry_service.champion_version()
    if version is None:
        raise NoModelError("No champion model is deployed yet. Train a model first.")
    df = pd.DataFrame(rows)
    missing = [c for c in D.FEATURE_COLUMNS if c not in df.columns and c != "TotalCharges"]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    if "TotalCharges" not in df.columns:
        df["TotalCharges"] = None
    pipe = mlflow_service.load_pipeline(version)
    proba = pipe.predict_proba(df[D.FEATURE_COLUMNS])[:, 1]
    out = []
    for row, p in zip(df[D.FEATURE_COLUMNS].to_dict("records"), proba):
        clean = {k: _clean_value(v) for k, v in row.items()}
        rec = Prediction(model_version=version, input=clean, probability=float(p), label=int(p >= 0.5))
        db.add(rec)
        out.append(rec)
    db.commit()
    return {"model_version": version, "predictions": [
        {"id": r.id, "probability": r.probability, "label": r.label,
         "risk": "high" if r.probability >= 0.7 else "medium" if r.probability >= 0.4 else "low"} for r in out]}
