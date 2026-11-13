"""Thin wrapper around MLflow tracking + model registry (local SQLite backend or local server)."""
from __future__ import annotations

import threading

import mlflow
import mlflow.sklearn
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

from app.core.config import EXPERIMENT_NAME, MODEL_NAME, settings

_setup_done = False
_model_cache: dict[int, object] = {}
_lock = threading.Lock()


def setup() -> None:
    global _setup_done
    with _lock:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        if not _setup_done:
            if mlflow.get_experiment_by_name(EXPERIMENT_NAME) is None:
                remote = settings.mlflow_tracking_uri.startswith("http")
                mlflow.create_experiment(EXPERIMENT_NAME, artifact_location=None if remote else settings.mlruns_dir.as_uri())
            _setup_done = True
        mlflow.set_experiment(EXPERIMENT_NAME)


def client() -> MlflowClient:
    setup()
    return MlflowClient(tracking_uri=settings.mlflow_tracking_uri)


def alias_version(alias: str) -> int | None:
    try:
        return int(client().get_model_version_by_alias(MODEL_NAME, alias).version)
    except MlflowException:
        return None


def set_alias(alias: str, version: int) -> None:
    client().set_registered_model_alias(MODEL_NAME, alias, str(version))


def delete_alias(alias: str) -> None:
    try:
        client().delete_registered_model_alias(MODEL_NAME, alias)
    except MlflowException:
        pass


def set_version_tag(version: int, key: str, value: str) -> None:
    client().set_model_version_tag(MODEL_NAME, str(version), key, value)


def load_pipeline(version: int):
    """Load the sklearn pipeline of a registered version (cached; versions are immutable)."""
    if version not in _model_cache:
        setup()
        _model_cache[version] = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/{version}")
    return _model_cache[version]


def healthy() -> bool:
    try:
        client().get_experiment_by_name(EXPERIMENT_NAME)
        return True
    except Exception:  # noqa: BLE001
        return False
