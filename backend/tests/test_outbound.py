import contextlib
import json
import os
from unittest.mock import MagicMock

import pytest

from database import get_farmer, init_db, save_farmer
from telephony.outbound.agent import OutboundAgent, phone_number_from_metadata

# Use a test database path for unit testing
TEST_DB_PATH = "test_krushi_mitra_outbound.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Fixture to redirect the DB path to a test file and clean it up after each test."""
    monkeypatch.setattr("database.DB_PATH", TEST_DB_PATH)
    init_db()
    yield
    if os.path.exists(TEST_DB_PATH):
        with contextlib.suppress(Exception):
            os.remove(TEST_DB_PATH)


def test_phone_number_from_metadata():
    """Verify phone_number_from_metadata extracts phone numbers in JSON or plain string format."""
    mock_ctx = MagicMock()

    # Test valid JSON metadata
    mock_ctx.job.metadata = json.dumps({"phone_number": "+919999999999"})
    assert phone_number_from_metadata(mock_ctx) == "+919999999999"

    # Test plain text fallback metadata
    mock_ctx.job.metadata = " +919999999999 "
    assert phone_number_from_metadata(mock_ctx) == "+919999999999"

    # Test empty metadata
    mock_ctx.job.metadata = None
    assert phone_number_from_metadata(mock_ctx) is None


@pytest.mark.asyncio
async def test_outbound_agent_init_with_profile():
    """Verify OutboundAgent initializes system instructions with profile facts."""
    user_id = "+919999999999"

    # Save a farmer profile in the test DB
    save_farmer(
        user_id=user_id,
        name="Laxman",
        facts={"crops_grown": "cotton", "district": "Yavatmal", "land_size_acres": 8.0},
    )

    profile = get_farmer(user_id)
    assert profile is not None

    mock_ctx = MagicMock()

    # Instantiate OutboundAgent with profile
    agent = OutboundAgent(
        ctx=mock_ctx,
        user_id=user_id,
        profile=profile,
        last_summary="Discussed pesticide guidelines.",
    )

    # Verify name, crop, and last call details are successfully injected into prompt
    instructions = agent.instructions
    assert "Laxman" in instructions
    assert "cotton" in instructions
    assert "Yavatmal" in instructions
    assert "8.0 acres" in instructions
    assert "Discussed pesticide guidelines." in instructions
    assert "RETURNING USER" in instructions
    assert "OUTBOUND CALL PURPOSE" in instructions


@pytest.mark.asyncio
async def test_outbound_agent_init_new_user():
    """Verify OutboundAgent initializes standard prompt when caller profile is missing."""
    mock_ctx = MagicMock()

    agent = OutboundAgent(
        ctx=mock_ctx, user_id="+918888888888", profile=None, last_summary=None
    )

    instructions = agent.instructions
    assert "OUTBOUND CALL PURPOSE" in instructions
    assert "RETURNING USER" not in instructions
    assert "Laxman" not in instructions
