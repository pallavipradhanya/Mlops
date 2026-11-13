"""Evidently data drift monitoring: reference (training sample) vs current (logged predictions)."""
from __future__ import annotations

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models import MonitoringReport, Prediction
from app.ml import data as D
from app.services import activity, mlflow_service, registry_service, settings_service

NUMERIC_COLS = ["tenure", "MonthlyCharges", "TotalCharges", "prediction"]
CATEGORICAL_COLS = D.CATEGORICAL_RAW + ["SeniorCitizen"]


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    out = df[D.FEATURE_COLUMNS + ["prediction"]].copy()
    for c in ["tenure", "MonthlyCharges", "TotalCharges", "prediction"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    for c in CATEGORICAL_COLS:
        out[c] = out[c].astype(str)
    return out[NUMERIC_COLS + CATEGORICAL_COLS]


def _parse(metrics: list[dict]) -> list[dict]:
    cols = []
    for m in metrics:
        cfg = m.get("config", {})
        if cfg.get("type", "").endswith("ValueDrift"):
            method, thr, val = cfg["method"], float(cfg["threshold"]), float(m["value"])
            drifted = val < thr if "p_value" in method else val >= thr
            cols.append({"column": cfg["column"], "method": method, "threshold": thr,
                         "value": val, "drifted": bool(drifted)})
    return cols


def run_monitoring(db: Session) -> MonitoringReport:
    cfg = settings_service.get_all(db)
    version = registry_service.champion_version()
    report = MonitoringReport(status="no_model", threshold=cfg["drift_share_threshold"])
    if version is None:
        report.message = "No champion model deployed yet."
        return _save(db, report)
    report.model_version = version

    ref_path = settings.models_dir / f"reference_v{version}.csv"
    if not ref_path.exists():
        report.status, report.message = "error", f"Reference data for model v{version} is missing."
        return _save(db, report)

    rows = (db.query(Prediction).filter(Prediction.model_version == version)
            .order_by(Prediction.id.desc()).limit(int(cfg["monitoring_window"])).all())
    report.current_rows = len(rows)
    if len(rows) < int(cfg["min_current_rows"]):
        report.status = "insufficient_data"
        report.message = (f"Only {len(rows)} predictions logged for model v{version}; "
                          f"at least {int(cfg['min_current_rows'])} are needed for a meaningful drift test.")
        return _save(db, report)

    try:
        from evidently import DataDefinition, Dataset, Report
        from evidently.presets import DataDriftPreset

        reference = pd.read_csv(ref_path)
        pipe = mlflow_service.load_pipeline(version)
        reference["prediction"] = pipe.predict_proba(reference[D.FEATURE_COLUMNS])[:, 1]
        current = pd.DataFrame([{**r.input, "prediction": r.probability} for r in rows])
        reference, current = _prepare(reference), _prepare(current)
        report.reference_rows = len(reference)

        definition = DataDefinition(numerical_columns=NUMERIC_COLS, categorical_columns=CATEGORICAL_COLS)
        snapshot = Report([DataDriftPreset()]).run(
            Dataset.from_pandas(current, data_definition=definition),
            Dataset.from_pandas(reference, data_definition=definition),
        )
        cols = _parse(snapshot.dict()["metrics"])
        feature_cols = [c for c in cols if c["column"] != "prediction"]
        pred = next((c for c in cols if c["column"] == "prediction"), None)
        share = sum(c["drifted"] for c in feature_cols) / max(len(feature_cols), 1)
        report.columns = cols
        report.drift_share = share
        report.dataset_drift = share >= cfg["drift_share_threshold"]
        report.prediction_drift = {
            **(pred or {}),
            "reference_mean": float(reference["prediction"].mean()), "current_mean": float(current["prediction"].mean()),
            "reference_positive_rate": float((reference["prediction"] >= 0.5).mean()),
            "current_positive_rate": float((current["prediction"] >= 0.5).mean()),
        }
        report.status = "completed"
        report.message = (f"{sum(c['drifted'] for c in feature_cols)} of {len(feature_cols)} features drifted "
                          f"({share:.0%}); threshold {cfg['drift_share_threshold']:.0%}.")
        db.add(report)
        db.flush()
        html = settings.reports_dir / f"drift_report_{report.id}.html"
        snapshot.save_html(str(html))
        report.html_path = str(html)
        db.commit()
        db.refresh(report)
        activity.log(db, "monitoring.completed", f"Drift report #{report.id}: {report.message}")
        return report
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        report = MonitoringReport(status="error", model_version=version, message=f"Drift analysis failed: {exc}",
                                  current_rows=len(rows), threshold=cfg["drift_share_threshold"])
        return _save(db, report)


def _save(db: Session, report: MonitoringReport) -> MonitoringReport:
    db.add(report)
    db.commit()
    db.refresh(report)
    activity.log(db, f"monitoring.{report.status}", f"Drift report #{report.id}: {report.message}")
    return report
