import contextlib
import os

import pytest

from agent import KrushiMitra
from database import create_escalation, get_db, init_db

# Redirect DB to a test file for isolation
TEST_DB_PATH = "test_krushi_mitra_escalation.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Fixture to redirect the DB path to a test file and clean it up after each test."""
    monkeypatch.setattr("database.DB_PATH", TEST_DB_PATH)
    init_db()
    yield
    if os.path.exists(TEST_DB_PATH):
        with contextlib.suppress(Exception):
            os.remove(TEST_DB_PATH)


def test_database_create_escalation():
    """Verify that create_escalation writes to the database correctly and returns the ticket ID."""
    ticket_id = create_escalation(
        user_id="test-farmer",
        reason="Severe Pink Bollworm damage",
        summary="Farmer reports 50% loss of cotton bolls in Akola.",
        urgency="HIGH",
    )
    assert ticket_id == 1

    # Query database directly to verify contents
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM escalations WHERE id = ?", (ticket_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row["user_id"] == "test-farmer"
    assert row["reason"] == "Severe Pink Bollworm damage"
    assert row["urgency"] == "HIGH"
    assert row["status"] == "PENDING"
    assert row["created_at"] is not None


@pytest.mark.asyncio
async def test_agent_create_escalation_tool():
    """Verify the agent's create_escalation tool operates correctly."""
    agent = KrushiMitra(user_id="test-farmer")

    res = await agent.create_escalation(
        reason="Pesticide recommendation request",
        summary="Farmer Laxman wants chemical pesticide brands for bollworm.",
        urgency="medium",
    )

    assert "Successfully created escalation ticket #1" in res

    # Check database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM escalations WHERE id = 1")
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row["urgency"] == "MEDIUM"  # Verify uppercase normalization
