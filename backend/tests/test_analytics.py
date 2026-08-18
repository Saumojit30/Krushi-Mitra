import contextlib
import json
import os

import pytest

from database import create_escalation, get_db, init_db, save_call_summary, save_farmer

# Use test DB file for isolation
TEST_DB_PATH = "test_krushi_mitra_analytics.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Fixture to redirect the DB path to a test file and clean it up after each test."""
    monkeypatch.setattr("database.DB_PATH", TEST_DB_PATH)
    monkeypatch.setattr("get_analytics.DB_PATH", TEST_DB_PATH)
    init_db()
    yield
    if os.path.exists(TEST_DB_PATH):
        with contextlib.suppress(Exception):
            os.remove(TEST_DB_PATH)


def test_save_call_summary_with_analytics():
    """Verify that save_call_summary records call duration, outcome, errors, and call type in SQLite."""
    user_id = "+919999999999"
    save_farmer(user_id=user_id, name="Laxman")

    # Save a successful inbound call summary
    save_call_summary(
        user_id=user_id,
        summary="Farmer Laxman successfully got weather forecast for Yavatmal.",
        duration_seconds=45,
        outcome="SUCCESS",
        error_log=None,
        call_type="INBOUND",
    )

    # Save a failed outbound warning alert call summary
    save_call_summary(
        user_id=user_id,
        summary="Farmer did not answer warning call.",
        duration_seconds=0,
        outcome="FAILURE",
        error_log="Call connected but no dialogue detected",
        call_type="OUTBOUND",
    )

    # Assert database records
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calls ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 2

    # Check first call (INBOUND SUCCESS)
    assert rows[0]["user_id"] == user_id
    assert rows[0]["duration_seconds"] == 45
    assert rows[0]["outcome"] == "SUCCESS"
    assert rows[0]["error_log"] is None
    assert rows[0]["call_type"] == "INBOUND"

    # Check second call (OUTBOUND FAILURE)
    assert rows[1]["user_id"] == user_id
    assert rows[1]["duration_seconds"] == 0
    assert rows[1]["outcome"] == "FAILURE"
    assert rows[1]["error_log"] == "Call connected but no dialogue detected"
    assert rows[1]["call_type"] == "OUTBOUND"


def test_get_analytics_script_output():
    """Verify that get_analytics.py aggregates call history statistics into correct JSON format."""
    user_id_1 = "+919999999999"
    user_id_2 = "+918888888888"

    save_farmer(user_id=user_id_1, name="Laxman")
    save_farmer(user_id=user_id_2, name="Namdev")

    # Add 3 calls: 2 SUCCESS, 1 FAILURE
    save_call_summary(
        user_id=user_id_1,
        summary="Success call 1",
        duration_seconds=30,
        outcome="SUCCESS",
        call_type="INBOUND",
    )
    save_call_summary(
        user_id=user_id_2,
        summary="Success call 2",
        duration_seconds=60,
        outcome="SUCCESS",
        call_type="INBOUND",
    )
    save_call_summary(
        user_id=user_id_1,
        summary="Failure call 3",
        duration_seconds=15,
        outcome="FAILURE",
        call_type="OUTBOUND",
    )

    # Add 1 pending escalation
    create_escalation(
        user_id=user_id_1,
        reason="Crop rot",
        summary="Rotting cotton bolls",
        urgency="HIGH",
    )

    # Execute get_analytics.py script and parse output
    # Since we are mock patching, let's call the main function of get_analytics directly!
    import sys
    from io import StringIO

    import get_analytics

    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    try:
        get_analytics.main()
    finally:
        sys.stdout = old_stdout

    output_json = json.loads(mystdout.getvalue().strip())

    assert output_json["total_calls"] == 3
    assert output_json["success_rate"] == 66.7
    assert output_json["avg_duration"] == 35.0
    assert output_json["inbound_count"] == 2
    assert output_json["outbound_count"] == 1
    assert output_json["pending_escalations"] == 1
    assert len(output_json["recent_calls"]) == 3
    assert output_json["recent_calls"][0]["farmer_name"] == "Laxman"
