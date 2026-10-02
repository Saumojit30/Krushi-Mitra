"""
Unit tests for non-blocking async IO, STT configuration, and latency tracking metrics.
"""

import pytest

from agent import get_stt_provider
from database import (
    async_create_escalation,
    async_get_farmer,
    async_get_last_call_summary,
    async_save_call_summary,
    async_save_farmer,
    init_db,
)
from logger import LatencyTracker
from rag_utility import query_pest_advisory_async


@pytest.mark.asyncio
async def test_async_database_helpers():
    """Verify that async database helpers execute cleanly without blocking."""
    init_db()
    test_user = "test_async_user_123"

    # Save farmer
    await async_save_farmer(
        user_id=test_user,
        name="Santosh",
        language_preference="mr",
        facts={"crops_grown": "cotton", "land_size_acres": 5},
    )

    # Get farmer
    profile = await async_get_farmer(test_user)
    assert profile is not None
    assert profile["name"] == "Santosh"

    # Save summary
    await async_save_call_summary(
        user_id=test_user,
        summary="Farmer asked about pink bollworm prevention.",
        duration_seconds=15,
        outcome="SUCCESS",
    )

    # Get last call summary
    summary = await async_get_last_call_summary(test_user)
    assert summary == "Farmer asked about pink bollworm prevention."

    # Create escalation
    ticket_id = await async_create_escalation(
        user_id=test_user,
        reason="Pink bollworm infestation",
        summary="Over 20% fields damaged.",
        urgency="HIGH",
    )
    assert ticket_id > 0


@pytest.mark.asyncio
async def test_async_rag_utility():
    """Verify local advisories query returns structured result asynchronously."""
    result = await query_pest_advisory_async("pink bollworm")
    assert result is not None
    pest_name = result["pest_or_disease"].lower()
    assert "pink bollworm" in pest_name


def test_latency_tracker_metrics():
    """Verify LatencyTracker computes turn metrics accurately."""
    tracker = LatencyTracker()
    tracker.on_speech_end()

    # Simulate time progression
    tracker._current.user_speech_end_ts = 10.0
    tracker.on_llm_first_token()
    tracker._current.llm_first_token_ts = 10.3  # 300ms

    tracker.on_tts_first_audio()
    tracker._current.tts_first_audio_ts = 10.6  # 300ms tts, 600ms total

    turn = tracker._current
    assert turn.llm_latency_ms == 300.0
    assert turn.tts_latency_ms == 300.0
    assert turn.total_latency_ms == 600.0

    tracker.log_turn()
    summary = tracker.summary()
    assert summary["turns"] == 1
    assert summary["avg_total_ms"] == 600.0


def test_stt_provider_configuration(monkeypatch):
    """Verify STT_PROVIDER switches between deepgram and openai."""
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dummy_deepgram_key")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy_openai_key")

    monkeypatch.setenv("STT_PROVIDER", "deepgram")
    stt_deepgram = get_stt_provider()
    assert "deepgram" in type(stt_deepgram).__module__.lower()

    monkeypatch.setenv("STT_PROVIDER", "openai")
    stt_openai = get_stt_provider()
    assert "openai" in type(stt_openai).__module__.lower()
