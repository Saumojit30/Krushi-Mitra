import json
import os
import sqlite3
from datetime import datetime

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


def main():
    if supabase_client:
        try:
            # 1. Total Calls
            res = supabase_client.table("calls").select("id", count="exact").execute()
            total_calls = res.count or 0

            # 2. Success Rate
            res_success = (
                supabase_client.table("calls")
                .select("id", count="exact")
                .eq("outcome", "SUCCESS")
                .execute()
            )
            success_calls = res_success.count or 0
            success_rate = (
                round((success_calls / total_calls * 100), 1)
                if total_calls > 0
                else 0.0
            )

            # 3. Average Duration
            res_durations = (
                supabase_client.table("calls").select("duration_seconds").execute()
            )
            if res_durations.data:
                durations = [
                    r["duration_seconds"]
                    for r in res_durations.data
                    if r.get("duration_seconds") is not None
                ]
                avg_duration = (
                    round(sum(durations) / len(durations), 1) if durations else 0.0
                )
            else:
                avg_duration = 0.0

            # 4. Inbound vs Outbound
            res_inbound = (
                supabase_client.table("calls")
                .select("id", count="exact")
                .eq("call_type", "INBOUND")
                .execute()
            )
            inbound_count = res_inbound.count or 0
            res_outbound = (
                supabase_client.table("calls")
                .select("id", count="exact")
                .eq("call_type", "OUTBOUND")
                .execute()
            )
            outbound_count = res_outbound.count or 0

            # 5. Pending Escalations
            res_pending = (
                supabase_client.table("escalations")
                .select("id", count="exact")
                .eq("status", "PENDING")
                .execute()
            )
            pending_escalations = res_pending.count or 0

            # 6. Recent 10 Calls with farmer names joined
            # Supabase allows natural joining on foreign keys by specifying nested properties
            res_calls = (
                supabase_client.table("calls")
                .select(
                    "id, user_id, summary, duration_seconds, outcome, error_log, call_type, created_at, farmers(name)"
                )
                .order("created_at", desc=True)
                .limit(10)
                .execute()
            )

            recent_calls = []
            if res_calls.data:
                for row in res_calls.data:
                    created_at_str = row["created_at"]
                    try:
                        # Standardize datetime format for UI
                        dt = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        )
                        formatted_date = dt.strftime("%b %d, %I:%M %p")
                    except Exception:
                        formatted_date = created_at_str

                    farmer_obj = row.get("farmers") or {}
                    farmer_name = (
                        farmer_obj.get("name") if isinstance(farmer_obj, dict) else None
                    )
                    if not farmer_name:
                        farmer_name = "Unknown Farmer"

                    recent_calls.append(
                        {
                            "id": row["id"],
                            "user_id": row["user_id"],
                            "farmer_name": farmer_name,
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
            return
        except Exception as e:
            print(json.dumps({"error": f"Supabase analytics query failed: {e}"}))
            return

    # Fallback to local SQLite
    if not os.path.exists(DB_PATH):
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
        print(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    main()
