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


SQLITE_MAGIC = b"SQLite format 3\x00"


def _is_valid_sqlite(path: str) -> bool:
    """Quick sanity check: openable + readable schema."""
    import sqlite3
    try:
        c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        c.execute("SELECT count(*) FROM sqlite_master").fetchone()
        c.close()
        return True
    except Exception:
        return False


def _try_repair_utf8_mangled(path: str) -> bool:
    """Repair a DB corrupted by the OLD download button.

    The old UI built the download Blob from a binary STRING -> the browser
    UTF-8-encoded it, so every byte >= 0x80 became 2 bytes. That transform is
    exactly reversible: utf-8 decode -> latin-1 encode gives back the bytes.
    Returns True if a repaired copy at <path> now passes the SQLite check.
    """
    try:
        raw = open(path, "rb").read()
        repaired = raw.decode("utf-8").encode("latin-1")
        if not repaired.startswith(SQLITE_MAGIC):
            return False
        tmp = path + ".repaired"
        with open(tmp, "wb") as fh:
            fh.write(repaired)
        if _is_valid_sqlite(tmp):
            os.replace(tmp, path)
            return True
        os.unlink(tmp)
        return False
    except (UnicodeDecodeError, UnicodeEncodeError):
        return False


def import_db(source_path: str):
    """Validate then swap the active DB (with .bak backup of the current one).

    Raises ValueError with a human-readable message on invalid files.
    Auto-repairs files corrupted by the old UTF-8-mangling download button.
    """
    import shutil
    with _lock:
        if not os.path.exists(source_path) or os.path.getsize(source_path) == 0:
            raise ValueError("file is empty or missing")
        # 1) already valid?  2) else: try auto-repair (old download button
        # UTF-8 corruption) — the ASCII magic header survives mangling, so the
        # repair must be attempted whenever VALIDATION fails, not just when
        # the header differs.
        if not _is_valid_sqlite(source_path):
            if not _try_repair_utf8_mangled(source_path):
                raise ValueError(
                    "not a valid SQLite database "
                    "(database disk image is malformed). If this file was "
                    "downloaded with an OLD version of the web UI, it was "
                    "corrupted at download time and cannot always be "
                    "recovered — export a fresh one after updating."
                )
        if not _is_valid_sqlite(source_path):
            raise ValueError("database disk image is malformed (failing integrity read)")
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, DB_PATH + ".bak")  # safety net
        shutil.copy2(source_path, DB_PATH)
