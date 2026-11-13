"""sklearn pipelines, evaluation and a leakage-safe train/test split."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from app.ml.data import CATEGORICAL_MODEL, FEATURE_COLUMNS, NUMERIC_MODEL, TARGET, engineer_features

ALGORITHMS = ("logistic_regression", "random_forest")


def build_pipeline(algorithm: str, hyper: dict[str, Any], seed: int) -> Pipeline:
    if algorithm == "logistic_regression":
        clf = LogisticRegression(random_state=seed, **hyper)
    elif algorithm == "random_forest":
        clf = RandomForestClassifier(random_state=seed, n_jobs=1, **hyper)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    # Imputers/scalers/encoders live INSIDE the pipeline: they are fit on the training split only.
    prep = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), NUMERIC_MODEL),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_MODEL),
    ])
    return Pipeline([
        ("features", FunctionTransformer(engineer_features, validate=False)),
        ("prep", prep),
        ("clf", clf),
    ])


def split(df: pd.DataFrame, test_size: float, seed: int):
    X, y = df[FEATURE_COLUMNS], df[TARGET]
    return train_test_split(X, y, test_size=test_size, random_state=seed, stratify=y)


def evaluate(pipe: Pipeline, X: pd.DataFrame, y: pd.Series) -> tuple[dict[str, float], list[list[int]]]:
    proba = pipe.predict_proba(X)[:, 1]
    pred = (proba >= 0.5).astype(int)
    metrics = {
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, proba)),
    }
    cm = confusion_matrix(y, pred, labels=[0, 1]).tolist()
    return metrics, cm


def best_run(results: list[dict]) -> dict:
    return max(results, key=lambda r: (r["metrics"]["roc_auc"], r["metrics"]["f1"]))


__all__ = ["ALGORITHMS", "build_pipeline", "split", "evaluate", "best_run", "np"]
