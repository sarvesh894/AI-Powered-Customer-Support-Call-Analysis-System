"""SQLite = Agent 1 ka 'status register'. Har call ka status yahan track hota hai."""
import json
import sqlite3
import time
from config import DB_PATH, MAX_RETRIES

# Status: pending -> processing -> done | needs_review | failed


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS calls(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_hash TEXT UNIQUE,      -- file ke content ka SHA256 (duplicate roknay ke liye)
            file_name TEXT, file_path TEXT,
            status TEXT DEFAULT 'pending',
            reason TEXT,
            attempts INTEGER DEFAULT 0,
            analysis TEXT,
            created_at REAL, updated_at REAL)""")


def register_call(file_hash, file_name, file_path):
    """Nayi call ho to id return karta hai, pehle se dekhi hui ho to None."""
    try:
        with conn() as c:
            cur = c.execute(
                "INSERT INTO calls(file_hash,file_name,file_path,created_at,updated_at) VALUES(?,?,?,?,?)",
                (file_hash, file_name, str(file_path), time.time(), time.time()))
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_work():
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM calls WHERE status='pending' OR (status='failed' AND attempts<?) ORDER BY id",
            (MAX_RETRIES,))]


def set_status(call_id, status, reason=None, analysis=None):
    with conn() as c:
        c.execute(
            """UPDATE calls SET status=?, reason=?, analysis=COALESCE(?,analysis),
               attempts=attempts+?, updated_at=? WHERE id=?""",
            (status, reason, json.dumps(analysis) if analysis else None,
             1 if status == "failed" else 0, time.time(), call_id))


def done_calls():
    with conn() as c:
        rows = c.execute("SELECT id,file_name,analysis FROM calls WHERE status='done' ORDER BY id").fetchall()
    return [{"id": r["id"], "file_name": r["file_name"], "analysis": json.loads(r["analysis"])} for r in rows]


def all_calls():
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT id,file_name,status,reason,attempts,updated_at FROM calls ORDER BY id")]


def get_call(call_id):
    with conn() as c:
        r = c.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
    return dict(r) if r else None
