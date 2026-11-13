"""Model lifecycle on top of MLflow aliases: champion (live), previous (rollback target), challenger (candidate)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import ModelVersion
from app.services import activity, mlflow_service


def champion_version() -> int | None:
    return mlflow_service.alias_version("champion")


def _row(db: Session, version: int) -> ModelVersion:
    row = db.query(ModelVersion).filter(ModelVersion.version == version).first()
    if not row:
        raise ValueError(f"Model version {version} not found")
    return row


def stage_candidate(db: Session, version: int) -> str:
    """Manual training: first model goes live automatically, later ones wait as 'challenger'."""
    if champion_version() is None:
        promote(db, version, "First registered model; no champion existed")
        return "champion"
    old = mlflow_service.alias_version("challenger")
    if old and old != version:
        o = _row(db, old)
        if o.status == "challenger":
            o.status = "archived"
    mlflow_service.set_alias("challenger", version)
    _row(db, version).status = "challenger"
    db.commit()
    return "challenger"


def promote(db: Session, version: int, note: str | None = None) -> None:
    row = _row(db, version)
    if row.status == "rejected" and not note:
        note = "Manually promoted after rejection"
    current = champion_version()
    if current == version:
        return
    if current is not None:
        old_prev = mlflow_service.alias_version("previous")
        if old_prev and old_prev not in (current, version):
            p = _row(db, old_prev)
            p.status = "archived"
        mlflow_service.set_alias("previous", current)
        _row(db, current).status = "previous"
    if mlflow_service.alias_version("previous") == version:
        mlflow_service.delete_alias("previous")
    if mlflow_service.alias_version("challenger") == version:
        mlflow_service.delete_alias("challenger")
    mlflow_service.set_alias("champion", version)
    row.status = "champion"
    row.note = note
    db.commit()
    activity.log(db, "model.promoted", f"Model v{version} promoted to champion" + (f" ({note})" if note else ""))


def reject(db: Session, version: int, reason: str) -> None:
    row = _row(db, version)
    if row.status == "champion":
        raise ValueError("Cannot reject the live champion; promote another version or roll back")
    row.status, row.note = "rejected", reason
    if mlflow_service.alias_version("challenger") == version:
        mlflow_service.delete_alias("challenger")
    mlflow_service.set_version_tag(version, "status", "rejected")
    db.commit()
    activity.log(db, "model.rejected", f"Model v{version} rejected: {reason}")


def rollback(db: Session) -> int:
    prev, champ = mlflow_service.alias_version("previous"), champion_version()
    if prev is None or champ is None:
        raise ValueError("No previous model to roll back to")
    mlflow_service.set_alias("champion", prev)
    mlflow_service.set_alias("previous", champ)
    _row(db, prev).status, _row(db, champ).status = "champion", "previous"
    _row(db, prev).note = f"Rolled back from v{champ}"
    db.commit()
    activity.log(db, "model.rollback", f"Rolled back: v{prev} is champion again (v{champ} kept as previous)")
    return prev


def list_models(db: Session) -> list[dict]:
    return [m.to_dict() for m in db.query(ModelVersion).order_by(ModelVersion.version.desc()).all()]
