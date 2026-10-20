"""SQLite persistence for exam state, results and session data."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time

DB_PATH = os.environ.get("CKA_SIM_DB", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "exam_state.db"
))

_lock = threading.Lock()


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS session (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS questions (
        cert TEXT, exam TEXT, question_id TEXT,
        status TEXT DEFAULT 'pending',
        score REAL DEFAULT 0,
        hints_used INTEGER DEFAULT 0,
        updated_at REAL,
        PRIMARY KEY (cert, exam, question_id)
    )""")
    c.commit()
    return c


def save_session(**kwargs):
    with _lock:
        c = _conn()
        for k, v in kwargs.items():
            c.execute(
                "INSERT OR REPLACE INTO session (key, value, updated_at) VALUES (?, ?, ?)",
                (k, json.dumps(v), time.time()),
            )
        c.commit()
        c.close()


def load_session():
    with _lock:
        c = _conn()
        rows = c.execute("SELECT key, value FROM session").fetchall()
        c.close()
        return {k: json.loads(v) for k, v in rows}


def save_question(cert, exam, question_id, status, score, hints_used):
    with _lock:
        c = _conn()
        c.execute(
            "INSERT OR REPLACE INTO questions (cert, exam, question_id, status, score, hints_used, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cert, exam, question_id, status, score, hints_used, time.time()),
        )
        c.commit()
        c.close()


def load_questions(cert, exam):
    with _lock:
        c = _conn()
        rows = c.execute(
            "SELECT question_id, status, score, hints_used FROM questions WHERE cert=? AND exam=?",
            (cert, exam),
        ).fetchall()
        c.close()
        return {r[0]: {"status": r[1], "score": r[2], "hints_used": r[3]} for r in rows}


def reset_all():
    with _lock:
        c = _conn()
        c.execute("DELETE FROM session")
        c.execute("DELETE FROM questions")
        c.commit()
        c.close()


def export_db():
    return DB_PATH


def import_db(source_path):
    import shutil
    with _lock:
        shutil.copy2(source_path, DB_PATH)
