"""MCL Template Builder — tiny persistence backend.

Serves the single-page app and stores ONE shared schedule blob in SQLite.
No auth (single shared schedule, trusted network) — front it with a reverse
proxy / VPN if it needs to be locked down.
"""
import datetime
import json
import os
import sqlite3

from flask import Flask, jsonify, request, send_from_directory

DB_PATH = os.environ.get("DB_PATH", "/data/schedule.db")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
SCHEDULE_KEY = "schedule"  # single shared blob

app = Flask(__name__, static_folder=None)


def get_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS kv ("
            "  key TEXT PRIMARY KEY,"
            "  value TEXT NOT NULL,"
            "  updated_at TEXT NOT NULL"
            ")"
        )


# ----- API ------------------------------------------------------------------
@app.get("/api/schedule")
def get_schedule():
    with get_db() as conn:
        row = conn.execute(
            "SELECT value, updated_at FROM kv WHERE key = ?", (SCHEDULE_KEY,)
        ).fetchone()
    if not row:
        return jsonify({"data": None, "updated_at": None})
    return jsonify({"data": json.loads(row["value"]), "updated_at": row["updated_at"]})


@app.put("/api/schedule")
def put_schedule():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "body must be a JSON object"}), 400
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    value = json.dumps(payload, separators=(",", ":"))
    with get_db() as conn:
        conn.execute(
            "INSERT INTO kv (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (SCHEDULE_KEY, value, now),
        )
    return jsonify({"ok": True, "updated_at": now})


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True})


# ----- Static app -----------------------------------------------------------
@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(STATIC_DIR, path)


init_db()

if __name__ == "__main__":
    # Dev server. In the container we run under gunicorn (see Dockerfile).
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
