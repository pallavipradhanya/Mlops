"""Central configuration. Everything is local: paths, SQLite, MLflow."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(os.getenv("MLOPS_HOME", Path(__file__).resolve().parents[3])).resolve()

MODEL_NAME = "churn-model"
EXPERIMENT_NAME = "churn-prediction"

DEFAULT_PARAMS = {
    "data": {"test_size": 0.2, "random_state": 42},
    "train": {
        "random_state": 42,
        "logistic_regression": {"C": 1.0, "max_iter": 1000},
        "random_forest": {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 2},
    },
}


def load_params() -> dict:
    """Read params.yaml (shared with DVC). Falls back to defaults."""
    params = {k: dict(v) for k, v in DEFAULT_PARAMS.items()}
    path = ROOT / "params.yaml"
    if path.exists():
        loaded = yaml.safe_load(path.read_text()) or {}
        for section, values in loaded.items():
            if isinstance(values, dict) and isinstance(params.get(section), dict):
                params[section].update(values)
            else:
                params[section] = values
    return params


class Settings:
    def __init__(self) -> None:
        self.root = ROOT
        self.data_dir = ROOT / "data"
        self.uploads_dir = self.data_dir / "uploads"
        self.reports_dir = ROOT / "reports"
        self.models_dir = ROOT / "models"
        self.artifacts_dir = ROOT / "artifacts"
        self.mlruns_dir = ROOT / "mlruns"
        for d in (self.data_dir, self.uploads_dir, self.reports_dir, self.models_dir,
                  self.artifacts_dir, self.mlruns_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.database_url = os.getenv(
            "DATABASE_URL", f"sqlite:///{(self.artifacts_dir / 'mlops360.db').as_posix()}"
        )
        self.mlflow_tracking_uri = os.getenv(
            "MLFLOW_TRACKING_URI", f"sqlite:///{(self.artifacts_dir / 'mlflow.db').as_posix()}"
        )
        self.mlflow_ui_url = os.getenv("MLFLOW_UI_URL", "http://localhost:5000")
        self.cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        self.enable_scheduler = os.getenv("ENABLE_SCHEDULER", "1") == "1"


settings = Settings()
