from __future__ import annotations

import io
from collections import Counter
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import MODEL_NAME, settings
from app.database.db import get_db
from app.database.models import (ActivityLog, Dataset, Experiment, ModelVersion, MonitoringReport, Prediction,
                                 RetrainingRun)
from app.ml import data as D
from app.monitoring.drift import run_monitoring
from app.retraining import scheduler
from app.retraining.workflow import run_retraining
from app.schemas.schemas import (GenerateRequest, PredictionInput, RejectRequest, RetrainRequest, SAMPLE_INPUT,
                                 SettingsUpdate, TrainRequest)
from app.services import dataset_service, mlflow_service, prediction_service, registry_service, settings_service
from app.services.training_service import train_candidates

router = APIRouter(prefix="/api")


def _bad(exc: Exception, code: int = 400):
    raise HTTPException(status_code=code, detail=str(exc))


# ---------- system ----------
@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.query(Dataset).count()
    return {"status": "ok", "database": "ok", "mlflow": "ok" if mlflow_service.healthy() else "unreachable"}


@router.get("/system")
def system():
    import evidently, mlflow, sklearn, sys  # noqa: E401
    return {
        "mlflow_ui_url": settings.mlflow_ui_url, "mlflow_tracking_uri": settings.mlflow_tracking_uri,
        "database_url": settings.database_url.split("///")[-1] if settings.database_url.startswith("sqlite") else "external",
        "model_name": MODEL_NAME, "scheduler": scheduler.status(),
        "versions": {"python": sys.version.split()[0], "mlflow": mlflow.__version__,
                     "evidently": getattr(evidently, "__version__", "n/a"), "scikit-learn": sklearn.__version__},
        "paths": {"data": str(settings.data_dir), "reports": str(settings.reports_dir), "models": str(settings.models_dir)},
    }


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return {"values": settings_service.get_all(db), "defaults": settings_service.DEFAULTS, "limits": settings_service.LIMITS}


@router.put("/settings")
def put_settings(body: SettingsUpdate, db: Session = Depends(get_db)):
    try:
        values = settings_service.update(db, body.values)
    except ValueError as exc:
        _bad(exc, 422)
    if "schedule_hours" in body.values:
        scheduler.configure(values["schedule_hours"])
    return {"values": values, "scheduler": scheduler.status()}


@router.get("/activity")
def activity_log(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(min(limit, 200)).all()
    return [r.to_dict() for r in rows]


# ---------- overview ----------
@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    champ_v = registry_service.champion_version()
    champ = db.query(ModelVersion).filter(ModelVersion.version == champ_v).first() if champ_v else None
    last_report = db.query(MonitoringReport).order_by(MonitoringReport.id.desc()).first()
    last_retrain = db.query(RetrainingRun).order_by(RetrainingRun.id.desc()).first()
    per_day = Counter(p.created_at.date().isoformat() for p in
                      db.query(Prediction).order_by(Prediction.id.desc()).limit(5000).all())
    versions = db.query(ModelVersion).order_by(ModelVersion.version).all()
    return {
        "counts": {"datasets": db.query(Dataset).count(), "experiments": db.query(Experiment).count(),
                   "models": len(versions), "predictions": db.query(Prediction).count(),
                   "drift_reports": db.query(MonitoringReport).count(),
                   "retraining_runs": db.query(RetrainingRun).count()},
        "champion": champ.to_dict() if champ else None,
        "last_drift_report": last_report.to_dict() if last_report else None,
        "last_retraining": last_retrain.to_dict() if last_retrain else None,
        "model_history": [{"version": v.version, "status": v.status, **v.metrics} for v in versions],
        "predictions_per_day": [{"date": d, "count": c} for d, c in sorted(per_day.items())],
        "recent_activity": [a.to_dict() for a in db.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(8).all()],
    }


# ---------- datasets ----------
@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    return [d.to_dict() for d in db.query(Dataset).order_by(Dataset.id.desc()).all()]


@router.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...), name: str | None = Form(None), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        ds, created = dataset_service.save_upload(db, file.filename or "dataset.csv", content, name)
    except (ValueError, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        _bad(exc, 422)
    return {"dataset": ds.to_dict(), "created": created}


@router.post("/datasets/generate")
def generate_dataset(body: GenerateRequest, db: Session = Depends(get_db)):
    try:
        ds, created = dataset_service.generate(db, body.rows, body.seed, body.drift, body.name)
    except ValueError as exc:
        _bad(exc, 422)
    return {"dataset": ds.to_dict(), "created": created}


@router.post("/datasets/download-telco")
def download_telco(db: Session = Depends(get_db)):
    try:
        ds, created = dataset_service.fetch_ibm(db)
    except RuntimeError as exc:
        _bad(exc, 502)
    return {"dataset": ds.to_dict(), "created": created}


@router.get("/datasets/{dataset_id}/preview")
def preview_dataset(dataset_id: int, rows: int = 10, db: Session = Depends(get_db)):
    ds = db.get(Dataset, dataset_id)
    if not ds:
        _bad(ValueError("Dataset not found"), 404)
    df = pd.read_csv(ds.path)
    return {"columns": list(df.columns), "rows": df.head(min(rows, 50)).fillna("").astype(str).to_dict("records"),
            "missing": {c: int(v) for c, v in df.isna().sum().items() if v}}


# ---------- training & experiments ----------
@router.post("/train")
def train(body: TrainRequest, db: Session = Depends(get_db)):
    ds = db.get(Dataset, body.dataset_id)
    if not ds:
        _bad(ValueError("Dataset not found"), 404)
    try:
        res = train_candidates(db, ds, list(body.algorithms), trigger="manual")
        stage = registry_service.stage_candidate(db, res["version"])
    except ValueError as exc:
        _bad(exc, 422)
    return {"version": res["version"], "stage": stage, "best_algorithm": res["best"]["algorithm"],
            "runs": [{k: r[k] for k in ("algorithm", "run_id", "metrics", "confusion_matrix")} for r in res["results"]]}


@router.get("/experiments")
def experiments(db: Session = Depends(get_db)):
    return [e.to_dict() for e in db.query(Experiment).order_by(Experiment.id.desc()).all()]


# ---------- registry ----------
@router.get("/models")
def models(db: Session = Depends(get_db)):
    return {"model_name": MODEL_NAME, "champion_version": registry_service.champion_version(),
            "versions": registry_service.list_models(db)}


@router.post("/models/{version}/promote")
def promote(version: int, db: Session = Depends(get_db)):
    try:
        registry_service.promote(db, version, "Manually promoted")
    except ValueError as exc:
        _bad(exc, 404)
    return {"champion_version": registry_service.champion_version()}


@router.post("/models/{version}/reject")
def reject(version: int, body: RejectRequest, db: Session = Depends(get_db)):
    try:
        registry_service.reject(db, version, body.reason)
    except ValueError as exc:
        _bad(exc, 400)
    return {"ok": True}


@router.post("/models/rollback")
def rollback(db: Session = Depends(get_db)):
    try:
        v = registry_service.rollback(db)
    except ValueError as exc:
        _bad(exc, 409)
    return {"champion_version": v}


# ---------- predictions ----------
@router.get("/predict/sample")
def sample():
    return SAMPLE_INPUT


@router.post("/predict")
def predict(body: PredictionInput, db: Session = Depends(get_db)):
    try:
        res = prediction_service.predict_rows(db, [body.model_dump()])
    except prediction_service.NoModelError as exc:
        _bad(exc, 409)
    except ValueError as exc:
        _bad(exc, 422)
    return {"model_version": res["model_version"], **res["predictions"][0]}


@router.post("/predict/batch")
async def predict_batch(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = pd.read_csv(io.BytesIO(await file.read()))
        if len(df) > 5000:
            raise ValueError("Batch limit is 5000 rows")
        res = prediction_service.predict_rows(db, df.to_dict("records"))
    except prediction_service.NoModelError as exc:
        _bad(exc, 409)
    except (ValueError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        _bad(exc, 422)
    preds = res["predictions"]
    return {"model_version": res["model_version"], "count": len(preds),
            "churn_rate": sum(p["label"] for p in preds) / max(len(preds), 1)}


@router.get("/predictions")
def predictions(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(Prediction).order_by(Prediction.id.desc()).limit(min(limit, 500)).all()
    return {"total": db.query(Prediction).count(), "items": [r.to_dict() for r in rows]}


# ---------- monitoring ----------
@router.post("/monitoring/run")
def monitoring_run(db: Session = Depends(get_db)):
    return run_monitoring(db).to_dict()


@router.get("/monitoring/reports")
def monitoring_reports(db: Session = Depends(get_db)):
    return [r.to_dict() for r in db.query(MonitoringReport).order_by(MonitoringReport.id.desc()).limit(50).all()]


@router.get("/monitoring/reports/{report_id}/html", response_class=HTMLResponse)
def monitoring_html(report_id: int, db: Session = Depends(get_db)):
    r = db.get(MonitoringReport, report_id)
    if not r or not r.html_path or not Path(r.html_path).exists():
        _bad(ValueError("No HTML report for this entry"), 404)
    return FileResponse(r.html_path, media_type="text/html")


# ---------- retraining ----------
@router.post("/retraining/run")
def retraining_run(body: RetrainRequest, db: Session = Depends(get_db)):
    try:
        return run_retraining(db, body.trigger, body.dataset_id).to_dict()
    except RuntimeError as exc:
        _bad(exc, 409)
    except ValueError as exc:
        _bad(exc, 422)


@router.get("/retraining/history")
def retraining_history(db: Session = Depends(get_db)):
    return [r.to_dict() for r in db.query(RetrainingRun).order_by(RetrainingRun.id.desc()).limit(50).all()]
