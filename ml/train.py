"""Train the XGBoost RUL model (same pipeline as the original notebook) and save artifacts.

Usage: python ml/train.py [--data data] [--out artifacts]
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

INDEX = ["unit_nr", "time_cycles"]
SETTINGS = ["setting_1", "setting_2", "setting_3"]
SENSORS = [f"s_{i}" for i in range(1, 22)]
COLS = INDEX + SETTINGS + SENSORS


def load(path):
    return pd.read_csv(path, sep=r"\s+", header=None, names=COLS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="artifacts")
    args = ap.parse_args()
    data, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    train = load(data / "train_FD001.txt").drop(columns="setting_3")
    test = load(data / "test_FD001.txt")
    y_test = pd.read_csv(data / "RUL_FD001.txt", sep=r"\s+", header=None, names=["RUL"])["RUL"]

    train["RUL"] = train.groupby("unit_nr")["time_cycles"].transform("max") - train["time_cycles"]

    # Feature selection: |corr with RUL| >= 0.5 (excluding RUL itself and the index columns)
    corr = train.corr()["RUL"].abs()
    features = [c for c in corr[corr >= 0.5].index if c not in ("RUL", *INDEX)]

    X_train, y_train = train[features], train["RUL"].clip(upper=125)
    scaler = StandardScaler().fit(X_train)

    model = XGBRegressor(n_estimators=200, max_depth=3, learning_rate=0.1, random_state=42, n_jobs=-1)
    model.fit(scaler.transform(X_train), y_train)

    last = test.groupby("unit_nr").tail(1)
    pred = model.predict(scaler.transform(last[features]))
    rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
    r2 = float(r2_score(y_test, pred))
    print(f"features={features}\ntest RMSE={rmse:.2f} R2={r2:.3f}")

    joblib.dump({"model": model, "scaler": scaler, "features": features}, out / "model.joblib")
    (out / "metrics.json").write_text(json.dumps({"rmse": rmse, "r2": r2, "features": features}, indent=2))


if __name__ == "__main__":
    main()
