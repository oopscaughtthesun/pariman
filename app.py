import json
import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
# Render's Postgres URLs sometimes start with postgres:// — psycopg2 needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS masters (
            uid INTEGER PRIMARY KEY,
            persons JSONB NOT NULL
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value INTEGER
        )"""
    )
    conn.commit()
    cur.close()
    conn.close()


init_db()


@app.route("/")
def index():
    return render_template("index.html")


# ---------- Masters CRUD ----------

@app.route("/api/masters", methods=["GET"])
def get_all_masters():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT uid, persons FROM masters")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    result = [{"uid": r[0], "persons": r[1]} for r in rows]
    return jsonify(result)


@app.route("/api/masters/<int:uid>", methods=["GET"])
def get_one_master(uid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT uid, persons FROM masters WHERE uid=%s", (uid,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify(None)
    return jsonify({"uid": row[0], "persons": row[1]})


@app.route("/api/masters", methods=["POST"])
def put_master():
    rec = request.get_json(force=True)
    uid = rec["uid"]
    persons = rec.get("persons", [])
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO masters (uid, persons) VALUES (%s, %s)
           ON CONFLICT (uid) DO UPDATE SET persons = EXCLUDED.persons""",
        (uid, json.dumps(persons)),
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/masters/<int:uid>", methods=["DELETE"])
def delete_master(uid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM masters WHERE uid=%s", (uid,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})


# ---------- UID counter (meta) ----------

@app.route("/api/next-uid", methods=["POST"])
def next_uid():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM meta WHERE key='lastUID'")
    row = cur.fetchone()
    cur_val = row[0] if row else 999
    if not cur_val or cur_val < 1000:
        cur_val = 999
    cur_val += 1
    if cur_val > 10000:
        cur.close()
        conn.close()
        return jsonify({"error": "UID limit reached"}), 400
    cur.execute(
        """INSERT INTO meta (key, value) VALUES ('lastUID', %s)
           ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
        (cur_val,),
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"uid": cur_val})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
