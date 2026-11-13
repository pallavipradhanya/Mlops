"""Tests run fully isolated: temp project root, temp SQLite DB, temp MLflow store. No network needed."""
import io
import os
import pathlib
import tempfile

_TMP = tempfile.mkdtemp(prefix="mlops360-test-")
for var in ("MLFLOW_TRACKING_URI", "DATABASE_URL"):
    os.environ.pop(var, None)
os.environ["MLOPS_HOME"] = _TMP
os.environ["ENABLE_SCHEDULER"] = "0"
pathlib.Path(_TMP, "params.yaml").write_text("train:\n  random_forest:\n    n_estimators: 30\n    max_depth: 8\n")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def csv_bytes(df) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode()


@pytest.fixture(scope="session")
def trained(client):
    """Ensures a registered dataset and a champion model exist; returns the dataset dict."""
    ds = client.post("/api/datasets/generate", json={"rows": 1500, "seed": 1}).json()["dataset"]
    if client.get("/api/models").json()["champion_version"] is None:
        assert client.post("/api/train", json={"dataset_id": ds["id"]}).status_code == 200
    return ds
