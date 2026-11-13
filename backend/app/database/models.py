from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, default=1)
    path: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64))
    rows: Mapped[int] = mapped_column(Integer)
    columns: Mapped[int] = mapped_column(Integer)
    churn_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50))  # upload | synthetic | ibm-telco
    dvc_md5: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dvc_tracked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "version": self.version, "sha256": self.sha256,
            "rows": self.rows, "columns": self.columns, "churn_rate": self.churn_rate,
            "source": self.source, "dvc_tracked": self.dvc_tracked, "dvc_md5": self.dvc_md5,
            "created_at": iso(self.created_at),
        }


class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mlflow_run_id: Mapped[str] = mapped_column(String(64))
    algorithm: Mapped[str] = mapped_column(String(50))
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"), nullable=True)
    params: Mapped[dict] = mapped_column(JSON)
    metrics: Mapped[dict] = mapped_column(JSON)
    confusion_matrix: Mapped[list] = mapped_column(JSON)
    trigger: Mapped[str] = mapped_column(String(30), default="manual")
    registered_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "run_id": self.mlflow_run_id, "algorithm": self.algorithm,
            "dataset_id": self.dataset_id, "params": self.params, "metrics": self.metrics,
            "confusion_matrix": self.confusion_matrix, "trigger": self.trigger,
            "registered_version": self.registered_version, "created_at": iso(self.created_at),
        }


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, unique=True)
    run_id: Mapped[str] = mapped_column(String(64))
    algorithm: Mapped[str] = mapped_column(String(50))
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="challenger")  # champion|previous|challenger|rejected|archived
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    def to_dict(self) -> dict:
        return {
            "version": self.version, "run_id": self.run_id, "algorithm": self.algorithm,
            "dataset_id": self.dataset_id, "metrics": self.metrics, "status": self.status,
            "note": self.note, "created_at": iso(self.created_at),
        }


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_version: Mapped[int] = mapped_column(Integer)
    input: Mapped[dict] = mapped_column(JSON)
    probability: Mapped[float] = mapped_column(Float)
    label: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "model_version": self.model_version, "input": self.input,
            "probability": self.probability, "label": self.label, "created_at": iso(self.created_at),
        }


class MonitoringReport(Base):
    __tablename__ = "monitoring_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(30))  # completed | insufficient_data | no_model | error
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference_rows: Mapped[int] = mapped_column(Integer, default=0)
    current_rows: Mapped[int] = mapped_column(Integer, default=0)
    dataset_drift: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    drift_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    columns: Mapped[list | None] = mapped_column(JSON, nullable=True)
    prediction_drift: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    html_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "status": self.status, "message": self.message,
            "model_version": self.model_version, "reference_rows": self.reference_rows,
            "current_rows": self.current_rows, "dataset_drift": self.dataset_drift,
            "drift_share": self.drift_share, "threshold": self.threshold,
            "columns": self.columns, "prediction_drift": self.prediction_drift,
            "has_html": bool(self.html_path), "created_at": iso(self.created_at),
        }


class RetrainingRun(Base):
    __tablename__ = "retraining_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger: Mapped[str] = mapped_column(String(30))  # manual | drift | scheduled
    status: Mapped[str] = mapped_column(String(30))  # skipped | promoted | rejected | error
    drift_detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    dataset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    champion_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    champion_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "trigger": self.trigger, "status": self.status,
            "drift_detected": self.drift_detected, "dataset_id": self.dataset_id,
            "candidate_version": self.candidate_version, "champion_version": self.champion_version,
            "candidate_metrics": self.candidate_metrics, "champion_metrics": self.champion_metrics,
            "reason": self.reason, "created_at": iso(self.created_at),
        }


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event: Mapped[str] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    def to_dict(self) -> dict:
        return {"id": self.id, "event": self.event, "message": self.message, "created_at": iso(self.created_at)}


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))
