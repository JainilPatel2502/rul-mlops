import os
from pathlib import Path

os.environ["MODEL_PATH"] = str(Path(__file__).resolve().parents[2] / "artifacts" / "model.joblib")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SAMPLE = dict(s_2=642.5, s_3=1590.0, s_4=1410.0, s_7=553.0, s_8=2388.0, s_11=47.5,
              s_12=521.5, s_13=2388.0, s_15=8.42, s_17=392, s_20=38.9, s_21=23.3)


def test_health_and_predict():
    with TestClient(app) as c:
        h = c.get("/health").json()
        assert h["status"] == "ok" and h["model_loaded"]
        r = c.post("/predict", json=SAMPLE)
        assert r.status_code == 200
        assert 0 <= r.json()["rul"] <= 200


def test_validation_error():
    with TestClient(app) as c:
        assert c.post("/predict", json={"s_2": 1}).status_code == 422


def test_metrics_exposed():
    with TestClient(app) as c:
        c.post("/predict", json=SAMPLE)
        body = c.get("/metrics/").text
        assert "rul_predictions_total" in body
