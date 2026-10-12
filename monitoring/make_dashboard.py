"""Generates monitoring/grafana/dashboards/rul.json (run: python monitoring/make_dashboard.py)."""
import json
from pathlib import Path

DS = {"type": "prometheus", "uid": "prometheus"}


def panel(i, title, expr, x, y, w=8, kind="timeseries", unit=None, legend=""):
    p = {
        "id": i, "type": kind, "title": title, "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": 8},
        "targets": [{"expr": expr, "legendFormat": legend, "refId": "A", "datasource": DS}],
        "fieldConfig": {"defaults": {}, "overrides": []},
    }
    if unit:
        p["fieldConfig"]["defaults"]["unit"] = unit
    return p


dist = panel(7, "Predicted RUL distribution", "histogram_quantile(0.5, sum(rate(rul_predicted_cycles_bucket[5m])) by (le))",
             0, 16, w=12, legend="p50")
dist["targets"].append({"expr": "histogram_quantile(0.9, sum(rate(rul_predicted_cycles_bucket[5m])) by (le))",
                        "legendFormat": "p90", "refId": "B", "datasource": DS})

dash = {
    "title": "RUL Model Serving", "uid": "rul-serving", "schemaVersion": 39, "version": 1,
    "refresh": "5s", "time": {"from": "now-15m", "to": "now"},
    "panels": [
        panel(1, "Predictions / sec", "rate(rul_predictions_total[1m])", 0, 0),
        panel(2, "Inference latency p95",
              "histogram_quantile(0.95, sum(rate(rul_prediction_latency_seconds_bucket[1m])) by (le))", 8, 0, unit="s"),
        panel(3, "Errors / sec", "rate(rul_prediction_errors_total[1m])", 16, 0),
        panel(4, "Last predicted RUL (cycles)", "rul_last_prediction_cycles", 0, 8, kind="stat"),
        panel(5, "Database up", "rul_db_up", 8, 8, kind="stat"),
        panel(6, "Total predictions", "rul_predictions_total", 16, 8, kind="stat"),
        dist,
        panel(8, "Backend scrape up", 'up{job="rul-backend"}', 12, 16, w=12, kind="stat"),
    ],
}
out = Path(__file__).parent / "grafana" / "dashboards" / "rul.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(dash, indent=2))
