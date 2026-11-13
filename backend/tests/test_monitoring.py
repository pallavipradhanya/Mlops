import os

from app.ml import data as D
from tests.conftest import csv_bytes


def _log(client, df):
    r = client.post("/api/predict/batch", files={"file": ("b.csv", csv_bytes(df.drop(columns=["Churn"], errors="ignore")), "text/csv")})
    assert r.status_code == 200, r.text
    return r.json()


def test_a_insufficient_data_is_reported_not_faked(client, trained):
    client.put("/api/settings", json={"values": {"min_current_rows": 500}})
    rep = client.post("/api/monitoring/run").json()
    assert rep["status"] == "insufficient_data"
    assert rep["dataset_drift"] is None and rep["columns"] is None and not rep["has_html"]
    assert "at least 500" in rep["message"]
    client.put("/api/settings", json={"values": {"min_current_rows": 50}})


def test_b_same_distribution_is_not_dataset_drift(client, trained):
    client.put("/api/settings", json={"values": {"monitoring_window": 300}})
    _log(client, D.generate_synthetic(300, seed=11, with_target=False))
    rep = client.post("/api/monitoring/run").json()
    assert rep["status"] == "completed", rep
    assert rep["dataset_drift"] is False and rep["drift_share"] < 0.3
    assert rep["has_html"] and rep["reference_rows"] > 0 and rep["current_rows"] == 300
    html = client.get(f"/api/monitoring/reports/{rep['id']}/html")
    assert html.status_code == 200 and "<html" in html.text.lower()


def test_c_shifted_distribution_is_detected(client, trained):
    _log(client, D.generate_synthetic(300, seed=12, drift=True, with_target=False))
    rep = client.post("/api/monitoring/run").json()
    assert rep["status"] == "completed"
    assert rep["dataset_drift"] is True and rep["drift_share"] >= 0.3
    drifted = {c["column"] for c in rep["columns"] if c["drifted"]}
    assert {"MonthlyCharges", "tenure"} <= drifted
    assert rep["prediction_drift"]["current_mean"] != rep["prediction_drift"]["reference_mean"]


def test_d_reports_listed_and_html_404(client, trained):
    reports = client.get("/api/monitoring/reports").json()
    assert len(reports) >= 3 and reports[0]["id"] > reports[-1]["id"]
    insufficient = next(r for r in reports if r["status"] == "insufficient_data")
    assert client.get(f"/api/monitoring/reports/{insufficient['id']}/html").status_code == 404
