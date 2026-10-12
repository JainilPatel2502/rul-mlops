import logging
import os

import psycopg

log = logging.getLogger("db")

DSN = os.getenv("DATABASE_URL", "")

SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id          SERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    inputs      JSONB NOT NULL,
    rul         DOUBLE PRECISION NOT NULL,
    latency_ms  DOUBLE PRECISION NOT NULL
)
"""


def init() -> bool:
    if not DSN:
        return False
    try:
        with psycopg.connect(DSN, connect_timeout=3) as conn:
            conn.execute(SCHEMA)
        return True
    except Exception as e:  # DB is optional for serving predictions
        log.warning("db init failed: %s", e)
        return False


def save(inputs: dict, rul: float, latency_ms: float) -> bool:
    if not DSN:
        return False
    try:
        with psycopg.connect(DSN, connect_timeout=3) as conn:
            conn.execute(
                "INSERT INTO predictions (inputs, rul, latency_ms) VALUES (%s::jsonb, %s, %s)",
                (psycopg.types.json.Jsonb(inputs), rul, latency_ms),
            )
        return True
    except Exception as e:
        log.warning("db save failed: %s", e)
        return False


def history(limit: int = 20) -> list[dict]:
    if not DSN:
        return []
    with psycopg.connect(DSN, connect_timeout=3) as conn:
        rows = conn.execute(
            "SELECT id, created_at, rul, latency_ms FROM predictions ORDER BY id DESC LIMIT %s", (limit,)
        ).fetchall()
    return [{"id": r[0], "created_at": r[1].isoformat(), "rul": r[2], "latency_ms": r[3]} for r in rows]


def ping() -> bool:
    if not DSN:
        return False
    try:
        with psycopg.connect(DSN, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
