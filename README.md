# Turbofan RUL – MLOps Demo

Serves an XGBoost Remaining-Useful-Life model (NASA C-MAPSS FD001) with a full MLOps stack.

```
browser ──► nginx (frontend :8081) ──/api──► FastAPI (backend :8000) ──► PostgreSQL (prediction log)
                                                  │ /metrics
                                  Prometheus :9090 ◄┘──► Grafana :3000
```

| Piece | Tech |
|---|---|
| Model training | `ml/train.py` → `artifacts/model.joblib` (model + scaler + feature list) |
| API | FastAPI, Prometheus client, psycopg |
| Frontend | static HTML served by nginx, reverse-proxying `/api/` |
| Database | `postgres:16-alpine` (stores every prediction) |
| Monitoring | Prometheus scrapes `/metrics/`; Grafana dashboard auto-provisioned |
| CI/CD | Jenkins (`Jenkinsfile`): lint → train → tests → build → compose integration test → push images |

## Run

```bash
docker compose up -d --build
```

- App: http://localhost:8081 (change with `FRONTEND_PORT`)
- API docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin / admin) → dashboard **RUL Model Serving**

Generate traffic for the dashboard:

```bash
for i in $(seq 1 50); do curl -s -X POST localhost:8081/api/predict -H 'Content-Type: application/json' \
  -d '{"s_2":642.5,"s_3":1590,"s_4":1410,"s_7":553,"s_8":2388,"s_11":47.5,"s_12":521.5,"s_13":2388,"s_15":8.42,"s_17":392,"s_20":38.9,"s_21":23.3}'; done
```

## Develop

```bash
pip install -r backend/requirements-dev.txt
python ml/train.py            # retrain, writes artifacts/
cd backend && pytest
```

Metrics exposed: `rul_predictions_total`, `rul_prediction_latency_seconds`, `rul_prediction_errors_total`,
`rul_last_prediction_cycles`, `rul_predicted_cycles` (histogram), `rul_db_up`.

## CI/CD (Jenkins)

The pipeline is fully containerised: the Jenkins agent only needs **Docker Desktop** (no Python or pip on the host).
`Dockerfile.ci` builds a toolbox image; lint, training, tests and the smoke test all run inside it, and the app
is built/started with `docker compose`. Stages: Build CI image → Lint → Train model → Unit tests (JUnit report) →
Build app images → Integration test (throw-away compose stack `rul-ci`, smoke test run on its Docker network) → Publish images.

Setup: **New Item → Pipeline → Pipeline script from SCM** (or paste the Jenkinsfile) pointing at this repo.
To enable publishing, set `DOCKERHUB_USER` in the Jenkinsfile and add a *Username with password* credential with id `dockerhub`.
