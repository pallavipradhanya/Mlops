import numpy as np
import pandas as pd
import pytest

from app.ml import data as D
from app.ml.pipeline import best_run, build_pipeline, evaluate, split


@pytest.fixture(scope="module")
def df():
    return D.clean_dataframe(D.generate_synthetic(1200, seed=3))


def test_synthetic_schema_and_blank_total_charges():
    raw = D.generate_synthetic(800, seed=5)
    assert not D.missing_columns(raw)
    assert (raw["TotalCharges"] == " ").any()  # mirrors the IBM data quirk
    assert 0.1 < (raw["Churn"] == "Yes").mean() < 0.5


def test_synthetic_is_reproducible():
    pd.testing.assert_frame_equal(D.generate_synthetic(200, seed=1), D.generate_synthetic(200, seed=1))


def test_clean_maps_target_and_dedupes():
    raw = D.generate_synthetic(300, seed=2)
    raw = pd.concat([raw, raw.iloc[:5]])
    raw.loc[raw.index[0], "Churn"] = "maybe"
    out = D.clean_dataframe(raw)
    assert set(out["Churn"].unique()) <= {0, 1}
    assert out["customerID"].is_unique and len(out) == 299


def test_engineer_features_handles_missing_and_new_customers():
    raw = D.generate_synthetic(300, seed=4)
    raw.loc[raw.index[:3], "tenure"] = 0
    raw.loc[raw.index[:3], "TotalCharges"] = " "
    raw.loc[raw.index[3], "Contract"] = None
    feats = D.engineer_features(raw)
    assert list(feats.columns) == D.NUMERIC_MODEL + D.CATEGORICAL_MODEL
    assert (feats.loc[feats.index[:3], "TotalCharges"] == 0).all()
    assert feats.loc[feats.index[3], "Contract"] == "Unknown"
    assert not feats[["avg_monthly_spend", "n_addons"]].isna().any().any()


def test_models_learn_something_and_metrics_are_valid(df):
    Xtr, Xte, ytr, yte = split(df, 0.2, 42)
    for algo, hyper in [("logistic_regression", {"C": 1.0, "max_iter": 500}),
                        ("random_forest", {"n_estimators": 40, "max_depth": 8})]:
        metrics, cm = evaluate(build_pipeline(algo, hyper, 42).fit(Xtr, ytr), Xte, yte)
        assert metrics["roc_auc"] > 0.65, algo
        assert all(0 <= v <= 1 for v in metrics.values())
        assert np.array(cm).sum() == len(yte)


def test_split_is_stratified_and_disjoint(df):
    Xtr, Xte, ytr, yte = split(df, 0.2, 42)
    assert not set(Xtr.index) & set(Xte.index)
    assert abs(ytr.mean() - yte.mean()) < 0.02


def test_training_is_reproducible(df):
    Xtr, Xte, ytr, yte = split(df, 0.2, 42)
    h = {"n_estimators": 20, "max_depth": 6}
    m1, _ = evaluate(build_pipeline("random_forest", h, 7).fit(Xtr, ytr), Xte, yte)
    m2, _ = evaluate(build_pipeline("random_forest", h, 7).fit(Xtr, ytr), Xte, yte)
    assert m1 == m2


def test_no_leakage_scaler_fit_on_train_only(df):
    Xtr, Xte, ytr, yte = split(df, 0.2, 42)
    pipe = build_pipeline("logistic_regression", {"max_iter": 300}, 42).fit(Xtr, ytr)
    scaler = pipe.named_steps["prep"].named_transformers_["num"].named_steps["sc"]
    idx = D.NUMERIC_MODEL.index("tenure")
    assert scaler.mean_[idx] == pytest.approx(D.engineer_features(Xtr)["tenure"].mean())
    assert scaler.mean_[idx] != pytest.approx(D.engineer_features(df[D.FEATURE_COLUMNS])["tenure"].mean())


def test_unknown_category_at_inference_does_not_crash(df):
    Xtr, Xte, ytr, _ = split(df, 0.2, 42)
    pipe = build_pipeline("logistic_regression", {"max_iter": 300}, 42).fit(Xtr, ytr)
    row = Xte.iloc[:2].copy()
    row["PaymentMethod"] = "Crypto"
    assert pipe.predict_proba(row).shape == (2, 2)


def test_best_run_prefers_auc_then_f1():
    a = {"metrics": {"roc_auc": 0.8, "f1": 0.5}}
    b = {"metrics": {"roc_auc": 0.8, "f1": 0.6}}
    c = {"metrics": {"roc_auc": 0.7, "f1": 0.9}}
    assert best_run([a, b, c]) is b
