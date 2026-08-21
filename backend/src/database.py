import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

# Supabase Imports and Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    from supabase import Client, create_client

    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase_client = None

DB_PATH = os.path.join(os.path.dirname(__file__), "krushi_mitra.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the database.
    If Supabase is configured, checks connection. Otherwise, initializes local SQLite tables.
    """
    if supabase_client:
        try:
            # Just do a simple query to verify Supabase connection
            supabase_client.table("farmers").select("user_id").limit(1).execute()
            print("Successfully connected to Supabase PostgreSQL database.")
        except Exception as e:
            print(f"Supabase connection test failed: {e}")
            print(
                "Please ensure you run the SQL DDL setup in your Supabase SQL editor."
            )
        return

    # Fallback to local SQLite
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
    if supabase_client:
        try:
            response = (
                supabase_client.table("farmers")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            if response.data:
                row = response.data[0]
                return {
                    "user_id": row["user_id"],
                    "name": row["name"],
                    "language_preference": row["language_preference"],
                    "facts": row["facts"] or {},
                    "last_interaction": row["last_interaction"],
                }
            return None
        except Exception as e:
            print(f"Supabase get_farmer error: {e}")
            return None

    # SQLite fallback
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
    now = datetime.now(timezone.utc).isoformat()

    if supabase_client:
        try:
            existing = get_farmer(user_id)
            if existing:
                updated_facts = existing["facts"] or {}
                if facts:
                    updated_facts.update(facts)

                updated_name = name if name is not None else existing["name"]
                updated_lang = (
                    language_preference
                    if language_preference is not None
                    else existing["language_preference"]
                )

                supabase_client.table("farmers").update(
                    {
                        "name": updated_name,
                        "language_preference": updated_lang,
                        "facts": updated_facts,
                        "last_interaction": now,
                    }
                ).eq("user_id", user_id).execute()
            else:
                updated_facts = facts or {}
                supabase_client.table("farmers").insert(
                    {
                        "user_id": user_id,
                        "name": name,
                        "language_preference": language_preference,
                        "facts": updated_facts,
                        "last_interaction": now,
                    }
                ).execute()
            return
        except Exception as e:
            print(f"Supabase save_farmer error: {e}")
            return

    # SQLite fallback
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM farmers WHERE user_id = ?", (user_id,))
    existing = cursor.fetchone()

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
    now = datetime.now(timezone.utc).isoformat()

    if supabase_client:
        try:
            # Ensure farmer exists
            existing = get_farmer(user_id)
            if not existing:
                save_farmer(user_id=user_id)

            supabase_client.table("calls").insert(
                {
                    "user_id": user_id,
                    "summary": summary,
                    "duration_seconds": duration_seconds,
                    "outcome": outcome.upper(),
                    "error_log": error_log,
                    "call_type": call_type.upper(),
                    "created_at": now,
                }
            ).execute()
            return
        except Exception as e:
            print(f"Supabase save_call_summary error: {e}")
            return

    # SQLite fallback
    conn = get_db()
    cursor = conn.cursor()
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
    if supabase_client:
        try:
            response = (
                supabase_client.table("calls")
                .select("summary")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0]["summary"]
            return None
        except Exception as e:
            print(f"Supabase get_last_call_summary error: {e}")
            return None

    # SQLite fallback
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
    now = datetime.now(timezone.utc).isoformat()

    if supabase_client:
        try:
            # Ensure farmer exists
            existing = get_farmer(user_id)
            if not existing:
                save_farmer(user_id=user_id)

            response = (
                supabase_client.table("escalations")
                .insert(
                    {
                        "user_id": user_id,
                        "reason": reason,
                        "summary": summary,
                        "urgency": urgency.upper(),
                        "created_at": now,
                    }
                )
                .execute()
            )
            if response.data:
                return response.data[0].get("id", 0)
            return 0
        except Exception as e:
            print(f"Supabase create_escalation error: {e}")
            return 0

    # SQLite fallback
    conn = get_db()
    cursor = conn.cursor()
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
