import contextlib
import os

import pytest

from agent import KrushiMitra
from database import (
    get_farmer,
    get_last_call_summary,
    init_db,
    save_call_summary,
    save_farmer,
)

# Use a test database path for unit testing to avoid polluting actual data
TEST_DB_PATH = "test_krushi_mitra.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Fixture to redirect the DB path to a test file and clean it up after each test."""
    monkeypatch.setattr("database.DB_PATH", TEST_DB_PATH)

    # Initialize schema
    init_db()

    yield

    # Clean up test DB file
    if os.path.exists(TEST_DB_PATH):
        with contextlib.suppress(Exception):
            os.remove(TEST_DB_PATH)


def test_sqlite_crud():
    """Test standard SQLite functions for profile retrieval, saving and history."""
    user_id = "test-farmer-123"

    # Assert initially empty
    assert get_farmer(user_id) is None
    assert get_last_call_summary(user_id) is None

    # Save profile details
    save_farmer(
        user_id=user_id,
        name="Namdev",
        language_preference="mr",
        facts={
            "crops_grown": "cotton",
            "land_size_acres": 5.0,
            "district": "Yavatmal",
            "irrigation_type": "rainfed",
        },
    )

    profile = get_farmer(user_id)
    assert profile is not None
    assert profile["name"] == "Namdev"
    assert profile["facts"]["crops_grown"] == "cotton"
    assert profile["facts"]["land_size_acres"] == 5.0
    assert profile["facts"]["district"] == "Yavatmal"

    # Verify updates merge facts rather than overwriting completely
    save_farmer(user_id=user_id, facts={"irrigation_type": "drip"})

    profile = get_farmer(user_id)
    assert profile["facts"]["irrigation_type"] == "drip"
    assert profile["facts"]["crops_grown"] == "cotton"  # Retained

    # Save call summaries
    save_call_summary(user_id, "Farmer asked about pink bollworm prevention.")
    save_call_summary(user_id, "Farmer inquired about CCI crop purchase procedures.")

    # Verify retrieval gets the last one
    last_summary = get_last_call_summary(user_id)
    assert last_summary == "Farmer inquired about CCI crop purchase procedures."


@pytest.mark.asyncio
async def test_agent_memory_tools():
    """Test that the agent can read and write profile details using its tools."""
    user_id = "test-agent-user"

    agent = KrushiMitra(user_id=user_id)

    # Test save_farmer_profile tool fails if consent is not given
    response = await agent.save_farmer_profile(
        name="Vitthal", crops_grown="cotton", consent_given=False
    )
    assert "Error" in response
    assert get_farmer(user_id) is None  # Nothing saved

    # Test save succeeds with consent_given=True
    response = await agent.save_farmer_profile(
        name="Vitthal", crops_grown="cotton", district="Amravati", consent_given=True
    )
    assert "Profile successfully saved/updated" in response

    profile = get_farmer(user_id)
    assert profile is not None
    assert profile["name"] == "Vitthal"
    assert profile["facts"]["district"] == "Amravati"

    # Test get_farmer_profile tool retrieves it
    profile_response = await agent.get_farmer_profile()
    assert "Vitthal" in profile_response
    assert "Amravati" in profile_response
