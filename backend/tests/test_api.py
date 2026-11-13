import pandas as pd

from app.ml import data as D
from tests.conftest import csv_bytes


def test_a_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["mlflow"] == "ok"


def test_b_predict_without_model_is_conflict(client):
    r = client.post("/api/predict", json=client.get("/api/predict/sample").json())
    assert r.status_code == 409
    assert "No champion" in r.json()["detail"]


def test_c_empty_state_endpoints(client):
    assert client.get("/api/datasets").json() == []
    ov = client.get("/api/overview").json()
    assert ov["champion"] is None and ov["counts"]["models"] == 0


def test_d_upload_rejects_bad_schema(client):
    bad = csv_bytes(pd.DataFrame({"a": [1, 2], "b": [3, 4]}))
    r = client.post("/api/datasets/upload", files={"file": ("bad.csv", bad, "text/csv")})
    assert r.status_code == 422
    assert "missing required columns" in r.json()["detail"]


def test_e_upload_valid_and_dedupe(client):
    content = csv_bytes(D.generate_synthetic(600, seed=99))
    r1 = client.post("/api/datasets/upload", files={"file": ("mine.csv", content, "text/csv")}, data={"name": "mine"})
    r2 = client.post("/api/datasets/upload", files={"file": ("mine.csv", content, "text/csv")}, data={"name": "mine"})
    assert r1.status_code == 200 and r1.json()["created"] is True
    assert r2.json()["created"] is False and r2.json()["dataset"]["id"] == r1.json()["dataset"]["id"]
    ds = r1.json()["dataset"]
    assert ds["rows"] == 600 and 0 < ds["churn_rate"] < 1 and len(ds["sha256"]) == 64


def test_f_dataset_preview(client):
    ds_id = client.get("/api/datasets").json()[0]["id"]
    body = client.get(f"/api/datasets/{ds_id}/preview").json()
    assert "tenure" in body["columns"] and len(body["rows"]) == 10


def test_g_train_registers_first_model_as_champion(client):
    ds = client.post("/api/datasets/generate", json={"rows": 1500, "seed": 1}).json()["dataset"]
    r = client.post("/api/train", json={"dataset_id": ds["id"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stage"] == "champion" and body["version"] == 1
    assert {run["algorithm"] for run in body["runs"]} == {"logistic_regression", "random_forest"}
    for run in body["runs"]:
        assert set(run["metrics"]) == {"accuracy", "precision", "recall", "f1", "roc_auc"}
        assert len(run["confusion_matrix"]) == 2
    assert len(client.get("/api/experiments").json()) == 2
    assert client.get("/api/models").json()["champion_version"] == 1


def test_h_second_model_is_challenger_then_promote_and_rollback(client):
    ds_id = client.get("/api/datasets").json()[0]["id"]
    body = client.post("/api/train", json={"dataset_id": ds_id, "algorithms": ["logistic_regression"]}).json()
    assert body["stage"] == "challenger" and body["version"] == 2
    assert client.get("/api/models").json()["champion_version"] == 1  # nothing promoted automatically
    assert client.post("/api/models/2/promote").json()["champion_version"] == 2
    statuses = {m["version"]: m["status"] for m in client.get("/api/models").json()["versions"]}
    assert statuses == {2: "champion", 1: "previous"}
    assert client.post("/api/models/rollback").json()["champion_version"] == 1
    assert client.post("/api/models/99/promote").status_code == 404


def test_i_train_unknown_dataset_404(client):
    assert client.post("/api/train", json={"dataset_id": 9999}).status_code == 404


def test_j_predict_valid(client):
    r = client.post("/api/predict", json=client.get("/api/predict/sample").json())
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["probability"] <= 1.0 and body["label"] in (0, 1) and body["risk"] in {"low", "medium", "high"}
    assert body["model_version"] == client.get("/api/models").json()["champion_version"]


def test_k_predict_validation(client):
    bad = client.get("/api/predict/sample").json()
    bad["tenure"] = -3
    assert client.post("/api/predict", json=bad).status_code == 422
    del bad["Contract"]
    assert client.post("/api/predict", json=bad).status_code == 422


def test_l_prediction_logged(client):
    body = client.get("/api/predictions").json()
    assert body["total"] >= 1 and "tenure" in body["items"][0]["input"]


def test_m_settings_validation(client):
    assert client.put("/api/settings", json={"values": {"min_roc_auc": 5}}).status_code == 422
    assert client.put("/api/settings", json={"values": {"nope": 1}}).status_code == 422
    ok = client.put("/api/settings", json={"values": {"drift_share_threshold": 0.3}})
    assert ok.status_code == 200 and ok.json()["values"]["drift_share_threshold"] == 0.3


def test_n_system_info(client):
    body = client.get("/api/system").json()
    assert body["model_name"] == "churn-model" and "mlflow" in body["versions"]
