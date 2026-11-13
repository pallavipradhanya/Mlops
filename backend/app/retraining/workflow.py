"""Local retraining workflow: drift check -> train candidate -> evaluate vs champion -> promote or reject."""
from __future__ import annotations

import threading

from sqlalchemy.orm import Session

from app.database.models import Dataset, RetrainingRun
from app.ml.pipeline import evaluate
from app.monitoring.drift import run_monitoring
from app.services import activity, dataset_service, mlflow_service, registry_service, settings_service
from app.services.training_service import train_candidates

_lock = threading.Lock()


def decide(candidate: dict, champion: dict | None, cfg: dict) -> tuple[bool, str]:
    """Promotion rules. Returns (promote?, reason). Drift alone never promotes anything."""
    problems = []
    if candidate["roc_auc"] < cfg["min_roc_auc"]:
        problems.append(f"ROC-AUC {candidate['roc_auc']:.3f} is below the required floor {cfg['min_roc_auc']:.2f}")
    if champion is not None:
        margin = cfg["min_improvement"]
        for m in ("f1", "roc_auc"):
            if candidate[m] < champion[m] + margin:
                problems.append(f"{m} {candidate[m]:.3f} does not beat champion {champion[m]:.3f} (required margin {margin:+.3f})")
    if problems:
        return False, "; ".join(problems)
    if champion is None:
        return True, "Passed the ROC-AUC floor and no champion exists"
    return True, "Candidate meets the ROC-AUC floor and is at least as good as the champion on F1 and ROC-AUC"


def run_retraining(db: Session, trigger: str = "manual", dataset_id: int | None = None,
                   overrides: dict | None = None) -> RetrainingRun:
    if trigger not in {"manual", "drift", "scheduled"}:
        raise ValueError("trigger must be manual, drift or scheduled")
    if not _lock.acquire(blocking=False):
        raise RuntimeError("A retraining run is already in progress")
    run = RetrainingRun(trigger=trigger, status="error")
    try:
        cfg = settings_service.get_all(db)
        dataset: Dataset | None = db.get(Dataset, dataset_id) if dataset_id else dataset_service.latest(db)
        if dataset is None:
            run.status, run.reason = "skipped", "No dataset registered. Upload or generate one first."
            return _finish(db, run)
        run.dataset_id = dataset.id
        champ_v = registry_service.champion_version()
        run.champion_version = champ_v

        if champ_v is not None:
            report = run_monitoring(db)
            run.drift_detected = report.dataset_drift if report.status == "completed" else None
            drift_note = report.message or report.status
        else:
            drift_note = "no champion deployed"

        if trigger == "drift" and not run.drift_detected:
            run.status = "skipped"
            run.reason = f"Drift-triggered run skipped: no dataset drift confirmed ({drift_note})"
            return _finish(db, run)
        if trigger == "scheduled" and not run.drift_detected and champ_v is not None:
            champ_row = next((m for m in registry_service.list_models(db) if m["version"] == champ_v), None)
            if champ_row and champ_row["dataset_id"] == dataset.id:
                run.status = "skipped"
                run.reason = "Scheduled run skipped: no drift and no new dataset since the champion was trained"
                return _finish(db, run)

        trained = train_candidates(db, dataset, trigger=trigger, overrides=overrides)
        version = trained["version"]
        run.candidate_version = version
        run.candidate_metrics = trained["best"]["metrics"]

        champion_metrics = None
        if champ_v is not None:
            champ_pipe = mlflow_service.load_pipeline(champ_v)
            champion_metrics, _ = evaluate(champ_pipe, trained["X_test"], trained["y_test"])
        run.champion_metrics = champion_metrics

        ok, reason = decide(run.candidate_metrics, champion_metrics, cfg)
        run.reason = reason
        if ok:
            registry_service.promote(db, version, f"{trigger} retraining: {reason}")
            run.status = "promoted"
        else:
            registry_service.reject(db, version, reason)
            run.status = "rejected"
        return _finish(db, run)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        run.status, run.reason = "error", f"{type(exc).__name__}: {exc}"
        return _finish(db, run)
    finally:
        _lock.release()


def _finish(db: Session, run: RetrainingRun) -> RetrainingRun:
    db.add(run)
    db.commit()
    db.refresh(run)
    activity.log(db, f"retraining.{run.status}", f"Retraining #{run.id} ({run.trigger}): {run.reason}")
    return run
