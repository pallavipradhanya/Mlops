from __future__ import annotations

import mlflow
import mlflow.sklearn
from sqlalchemy.orm import Session

from app.core.config import MODEL_NAME, load_params, settings
from app.database.models import Dataset, Experiment, ModelVersion
from app.ml import data as D
from app.ml.pipeline import ALGORITHMS, best_run, build_pipeline, evaluate, split
from app.services import activity, dataset_service, mlflow_service

PIP_REQS = ["scikit-learn", "pandas", "numpy"]


def train_candidates(db: Session, dataset: Dataset, algorithms: list[str] | None = None,
                     trigger: str = "manual", overrides: dict | None = None) -> dict:
    """Train every requested algorithm, log each run to MLflow, register the best as a new model version.

    The held-out test split is returned so a candidate and the current champion can be compared on identical data.
    """
    algorithms = algorithms or list(ALGORITHMS)
    for a in algorithms:
        if a not in ALGORITHMS:
            raise ValueError(f"Unknown algorithm '{a}'. Choose from {ALGORITHMS}")
    params = load_params()
    seed = int(params["train"]["random_state"])
    test_size = float(params["data"]["test_size"])
    df = dataset_service.load(dataset)
    if df[D.TARGET].nunique() < 2:
        raise ValueError("Dataset needs both churn and non-churn rows")
    X_train, X_test, y_train, y_test = split(df, test_size, int(params["data"]["random_state"]))

    mlflow_service.setup()
    results = []
    for algo in algorithms:
        hyper = {**params["train"][algo], **((overrides or {}).get(algo, {}))}
        with mlflow.start_run(run_name=f"{algo}-dataset{dataset.id}") as run:
            mlflow.log_params({f"{algo}.{k}": v for k, v in hyper.items()})
            mlflow.log_params({"algorithm": algo, "seed": seed, "test_size": test_size,
                               "train_rows": len(X_train), "test_rows": len(X_test)})
            mlflow.set_tags({
                "dataset_id": str(dataset.id), "dataset_name": dataset.name, "dataset_version": str(dataset.version),
                "dataset_sha256": dataset.sha256, "dvc_md5": dataset.dvc_md5 or "untracked", "trigger": trigger,
            })
            pipe = build_pipeline(algo, hyper, seed).fit(X_train, y_train)
            metrics, cm = evaluate(pipe, X_test, y_test)
            mlflow.log_metrics(metrics)
            mlflow.log_dict({"labels": [0, 1], "matrix": cm}, "confusion_matrix.json")
            info = mlflow.sklearn.log_model(pipe, name="model", pip_requirements=PIP_REQS,
                                          serialization_format="cloudpickle")
        results.append({"algorithm": algo, "run_id": run.info.run_id, "model_uri": info.model_uri,
                        "hyper": hyper, "metrics": metrics, "confusion_matrix": cm})

    best = best_run(results)
    mv = mlflow.register_model(best["model_uri"], MODEL_NAME)
    version = int(mv.version)
    mlflow_service.set_version_tag(version, "dataset_id", str(dataset.id))
    mlflow_service.set_version_tag(version, "algorithm", best["algorithm"])
    mlflow_service.set_version_tag(version, "trigger", trigger)

    # reference sample for drift monitoring = what this version was trained on
    ref = X_train.sample(min(2000, len(X_train)), random_state=seed)
    ref.to_csv(settings.models_dir / f"reference_v{version}.csv", index=False)

    for r in results:
        db.add(Experiment(
            mlflow_run_id=r["run_id"], algorithm=r["algorithm"], dataset_id=dataset.id, params=r["hyper"],
            metrics=r["metrics"], confusion_matrix=r["confusion_matrix"], trigger=trigger,
            registered_version=version if r is best else None,
        ))
    db.add(ModelVersion(version=version, run_id=best["run_id"], algorithm=best["algorithm"], dataset_id=dataset.id,
                        metrics=best["metrics"], status="challenger"))
    db.commit()
    activity.log(db, "training.completed",
                 f"Trained {', '.join(algorithms)} on dataset {dataset.id}; registered model v{version} "
                 f"({best['algorithm']}, ROC-AUC {best['metrics']['roc_auc']:.3f})")
    return {"version": version, "best": best, "results": results, "X_test": X_test, "y_test": y_test}
