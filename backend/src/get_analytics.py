import json
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "krushi_mitra.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def main():
    if not os.path.exists(DB_PATH):
        # Return empty metrics if database doesn't exist yet
        print(
            json.dumps(
                {
                    "total_calls": 0,
                    "success_rate": 0,
                    "avg_duration": 0,
                    "pending_escalations": 0,
                    "inbound_count": 0,
                    "outbound_count": 0,
                    "recent_calls": [],
                }
            )
        )
        return

    try:
        conn = get_db()
        cursor = conn.cursor()

        # 1. Total Calls
        cursor.execute("SELECT COUNT(*) FROM calls")
        total_calls = cursor.fetchone()[0]

        # 2. Success Rate
        cursor.execute("SELECT COUNT(*) FROM calls WHERE outcome = 'SUCCESS'")
        success_calls = cursor.fetchone()[0]
        success_rate = (
            round((success_calls / total_calls * 100), 1) if total_calls > 0 else 0.0
        )

        # 3. Average Duration
        cursor.execute("SELECT AVG(duration_seconds) FROM calls")
        avg_duration = round(cursor.fetchone()[0] or 0.0, 1)

        # 4. Inbound vs Outbound
        cursor.execute("SELECT COUNT(*) FROM calls WHERE call_type = 'INBOUND'")
        inbound_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM calls WHERE call_type = 'OUTBOUND'")
        outbound_count = cursor.fetchone()[0]

        # 5. Pending Escalations
        cursor.execute("SELECT COUNT(*) FROM escalations WHERE status = 'PENDING'")
        pending_escalations = cursor.fetchone()[0]

        # 6. Recent 10 Calls with farmer names joined
        cursor.execute("""
            SELECT c.id, c.user_id, c.summary, c.duration_seconds, c.outcome, c.error_log, c.call_type, c.created_at, f.name
            FROM calls c
            LEFT JOIN farmers f ON c.user_id = f.user_id
            ORDER BY c.created_at DESC
            LIMIT 10
        """)
        recent_calls = []
        for row in cursor.fetchall():
            # Format datetime
            created_at_str = row["created_at"]
            try:
                dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                formatted_date = dt.strftime("%b %d, %I:%M %p")
            except Exception:
                formatted_date = created_at_str

            recent_calls.append(
                {
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "farmer_name": row["name"] or "Unknown Farmer",
                    "summary": row["summary"],
                    "duration_seconds": row["duration_seconds"],
                    "outcome": row["outcome"],
                    "error_log": row["error_log"],
                    "call_type": row["call_type"],
                    "created_at": formatted_date,
                }
            )

        print(
            json.dumps(
                {
                    "total_calls": total_calls,
                    "success_rate": success_rate,
                    "avg_duration": avg_duration,
                    "pending_escalations": pending_escalations,
                    "inbound_count": inbound_count,
                    "outbound_count": outbound_count,
                    "recent_calls": recent_calls,
                }
            )
        )
        conn.close()
    except Exception as e:
        # Fallback error json
        print(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    main()
