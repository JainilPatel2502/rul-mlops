import os
import time
from contextlib import asynccontextmanager

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from pydantic import BaseModel

from . import db

MODEL_PATH = os.getenv("MODEL_PATH", "artifacts/model.joblib")

PREDICTIONS = Counter("rul_predictions_total", "Total RUL predictions served")
ERRORS = Counter("rul_prediction_errors_total", "Failed prediction requests")
LATENCY = Histogram("rul_prediction_latency_seconds", "Model inference latency")
LAST_RUL = Gauge("rul_last_prediction_cycles", "Most recent predicted RUL")
RUL_DIST = Histogram(
    "rul_predicted_cycles", "Distribution of predicted RUL", buckets=(10, 20, 30, 50, 75, 100, 125, 150)
)
DB_UP = Gauge("rul_db_up", "1 if PostgreSQL is reachable")

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.update(joblib.load(MODEL_PATH))
    DB_UP.set(1 if db.init() else 0)
    yield


app = FastAPI(title="Turbofan RUL API", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())


class Reading(BaseModel):
    """Sensor values of a single engine cycle (C-MAPSS FD001)."""

    s_2: float
    s_3: float
    s_4: float
    s_7: float
    s_8: float
    s_11: float
    s_12: float
    s_13: float
    s_15: float
    s_17: float
    s_20: float
    s_21: float


@app.get("/health")
def health():
    ok = db.ping()
    DB_UP.set(1 if ok else 0)
    return {"status": "ok", "model_loaded": "model" in state, "db": ok}


@app.post("/predict")
def predict(reading: Reading):
    start = time.perf_counter()
    try:
        row = pd.DataFrame([reading.model_dump()])[state["features"]]
        rul = float(state["model"].predict(state["scaler"].transform(row))[0])
    except Exception as e:
        ERRORS.inc()
        raise HTTPException(500, f"prediction failed: {e}")
    rul = max(rul, 0.0)
    elapsed = time.perf_counter() - start
    PREDICTIONS.inc()
    LATENCY.observe(elapsed)
    LAST_RUL.set(rul)
    RUL_DIST.observe(rul)
    saved = db.save(reading.model_dump(), rul, elapsed * 1000)
    DB_UP.set(1 if saved else 0)
    return {"rul": round(rul, 2), "stored": saved}


@app.get("/history")
def history(limit: int = 20):
    try:
        return db.history(min(limit, 100))
    except Exception as e:
        raise HTTPException(503, f"database unavailable: {e}")
