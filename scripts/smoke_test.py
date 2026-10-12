"""End-to-end smoke test of a running stack. Usage: python scripts/smoke_test.py [frontend_port] [prom_port] [grafana_port]"""
import json
import sys
import time
import urllib.request

fe, prom, graf = (sys.argv[1:4] + ["8081", "9090", "3000"][len(sys.argv[1:4]):])
SAMPLE = {"s_2": 642.5, "s_3": 1590, "s_4": 1410, "s_7": 553, "s_8": 2388, "s_11": 47.5,
          "s_12": 521.5, "s_13": 2388, "s_15": 8.42, "s_17": 392, "s_20": 38.9, "s_21": 23.3}


def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode()


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


health = json.loads(get(f"http://localhost:{fe}/api/health"))
assert health["model_loaded"] and health["db"], health
pred = post(f"http://localhost:{fe}/api/predict", SAMPLE)
assert 0 <= pred["rul"] <= 200 and pred["stored"], pred
assert json.loads(get(f"http://localhost:{fe}/api/history")), "history empty"
print("api OK:", pred)

for _ in range(12):  # wait for a Prometheus scrape
    if "rul_predictions_total" in get(f"http://localhost:{prom}/api/v1/query?query=rul_predictions_total") and \
            '"result":[]' not in get(f"http://localhost:{prom}/api/v1/query?query=rul_predictions_total"):
        break
    time.sleep(5)
else:
    sys.exit("prometheus has no rul_predictions_total")
print("prometheus OK")
assert json.loads(get(f"http://localhost:{graf}/api/health"))["database"] == "ok"
print("grafana OK")
