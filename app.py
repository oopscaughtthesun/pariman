import json
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DB_PATH = Path(__file__).parent / "data.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS masters (
            uid INTEGER PRIMARY KEY,
            persons TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value INTEGER
        )"""
    )
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    return render_template("index.html")


# ---------- Masters CRUD ----------

@app.route("/api/masters", methods=["GET"])
def get_all_masters():
    conn = get_conn()
    rows = conn.execute("SELECT uid, persons FROM masters").fetchall()
    conn.close()
    result = [{"uid": r["uid"], "persons": json.loads(r["persons"])} for r in rows]
    return jsonify(result)


@app.route("/api/masters/<int:uid>", methods=["GET"])
def get_one_master(uid):
    conn = get_conn()
    row = conn.execute("SELECT uid, persons FROM masters WHERE uid=?", (uid,)).fetchone()
    conn.close()
    if not row:
        return jsonify(None)
    return jsonify({"uid": row["uid"], "persons": json.loads(row["persons"])})


@app.route("/api/masters", methods=["POST"])
def put_master():
    rec = request.get_json(force=True)
    uid = rec["uid"]
    persons = rec.get("persons", [])
    conn = get_conn()
    conn.execute(
        "INSERT INTO masters (uid, persons) VALUES (?, ?) "
        "ON CONFLICT(uid) DO UPDATE SET persons=excluded.persons",
        (uid, json.dumps(persons)),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/masters/<int:uid>", methods=["DELETE"])
def delete_master(uid):
    conn = get_conn()
    conn.execute("DELETE FROM masters WHERE uid=?", (uid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ---------- UID counter (meta) ----------

@app.route("/api/next-uid", methods=["POST"])
def next_uid():
    conn = get_conn()
    row = conn.execute("SELECT value FROM meta WHERE key='lastUID'").fetchone()
    cur = row["value"] if row else 999
    if not cur or cur < 1000:
        cur = 999
    cur += 1
    if cur > 10000:
        conn.close()
        return jsonify({"error": "UID limit reached"}), 400
    conn.execute(
        "INSERT INTO meta (key, value) VALUES ('lastUID', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (cur,),
    )
    conn.commit()
    conn.close()
    return jsonify({"uid": cur})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
