import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "krushi_mitra.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            language_preference TEXT,
            facts TEXT,  -- JSON string containing: crops_grown, land_size_acres, district, irrigation_type
            last_interaction TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            summary TEXT,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES farmers(user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            summary TEXT NOT NULL,
            urgency TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES farmers(user_id)
        )
    """)

    # Run automatic SQLite schema migrations for call analytics columns
    cursor.execute("PRAGMA table_info(calls)")
    columns = [col[1] for col in cursor.fetchall()]
    if "duration_seconds" not in columns:
        cursor.execute(
            "ALTER TABLE calls ADD COLUMN duration_seconds INTEGER DEFAULT 0"
        )
    if "outcome" not in columns:
        cursor.execute("ALTER TABLE calls ADD COLUMN outcome TEXT DEFAULT 'SUCCESS'")
    if "error_log" not in columns:
        cursor.execute("ALTER TABLE calls ADD COLUMN error_log TEXT")
    if "call_type" not in columns:
        cursor.execute("ALTER TABLE calls ADD COLUMN call_type TEXT DEFAULT 'INBOUND'")

    conn.commit()
    conn.close()


def get_farmer(user_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM farmers WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row["user_id"],
            "name": row["name"],
            "language_preference": row["language_preference"],
            "facts": json.loads(row["facts"]) if row["facts"] else {},
            "last_interaction": row["last_interaction"],
        }
    return None


def save_farmer(
    user_id: str,
    name: Optional[str] = None,
    language_preference: Optional[str] = None,
    facts: Optional[dict] = None,
):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM farmers WHERE user_id = ?", (user_id,))
    existing = cursor.fetchone()

    now = datetime.now(timezone.utc).isoformat()

    if existing:
        existing_facts = json.loads(existing["facts"]) if existing["facts"] else {}
        if facts:
            existing_facts.update(facts)

        updated_name = name if name is not None else existing["name"]
        updated_lang = (
            language_preference
            if language_preference is not None
            else existing["language_preference"]
        )

        cursor.execute(
            """
            UPDATE farmers
            SET name = ?, language_preference = ?, facts = ?, last_interaction = ?
            WHERE user_id = ?
        """,
            (updated_name, updated_lang, json.dumps(existing_facts), now, user_id),
        )
    else:
        facts_str = json.dumps(facts) if facts else "{}"
        cursor.execute(
            """
            INSERT INTO farmers (user_id, name, language_preference, facts, last_interaction)
            VALUES (?, ?, ?, ?, ?)
        """,
            (user_id, name, language_preference, facts_str, now),
        )

    conn.commit()
    conn.close()


def save_call_summary(
    user_id: str,
    summary: str,
    duration_seconds: int = 0,
    outcome: str = "SUCCESS",
    error_log: Optional[str] = None,
    call_type: str = "INBOUND",
):
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        """
        INSERT INTO calls (user_id, summary, duration_seconds, outcome, error_log, call_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            user_id,
            summary,
            duration_seconds,
            outcome.upper(),
            error_log,
            call_type.upper(),
            now,
        ),
    )
    conn.commit()
    conn.close()


def get_last_call_summary(user_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT summary FROM calls
        WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 1
    """,
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["summary"]
    return None


def create_escalation(user_id: str, reason: str, summary: str, urgency: str) -> int:
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        """
        INSERT INTO escalations (user_id, reason, summary, urgency, created_at)
        VALUES (?, ?, ?, ?, ?)
    """,
        (user_id, reason, summary, urgency.upper(), now),
    )
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ticket_id
