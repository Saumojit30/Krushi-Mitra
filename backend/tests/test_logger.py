"""
Tests for Krushi Mitra latency logger.
Verifies tracking logic without any LiveKit or API dependencies.

Run with: uv run pytest tests/test_logger.py -v
"""

import time

from logger import LatencyTracker, TurnLatency


class TestTurnLatency:
    """Test the TurnLatency dataclass computed properties."""

    def test_llm_latency_computed_correctly(self):
        turn = TurnLatency(turn_id=1)
        turn.user_speech_end_ts = 1000.0
        turn.llm_first_token_ts = 1000.3  # 300ms
        turn.tts_first_audio_ts = 1000.5
        assert turn.llm_latency_ms == 300.0

    def test_tts_latency_computed_correctly(self):
        turn = TurnLatency(turn_id=1)
        turn.user_speech_end_ts = 1000.0
        turn.llm_first_token_ts = 1000.3
        turn.tts_first_audio_ts = 1000.5  # 200ms after llm
        assert turn.tts_latency_ms == 200.0

    def test_total_latency_computed_correctly(self):
        turn = TurnLatency(turn_id=1)
        turn.user_speech_end_ts = 1000.0
        turn.llm_first_token_ts = 1000.3
        turn.tts_first_audio_ts = 1000.5  # 500ms total
        assert turn.total_latency_ms == 500.0

    def test_returns_none_when_timestamps_missing(self):
        turn = TurnLatency(turn_id=1)
        # No timestamps set
        assert turn.llm_latency_ms is None
        assert turn.tts_latency_ms is None
        assert turn.total_latency_ms is None

    def test_partial_timestamps_return_none(self):
        turn = TurnLatency(turn_id=1)
        turn.user_speech_end_ts = 1000.0
        # llm_first_token_ts not set
        assert turn.llm_latency_ms is None
        assert turn.total_latency_ms is None


class TestLatencyTracker:
    """Test the LatencyTracker state machine."""

    def test_initial_state_empty(self):
        tracker = LatencyTracker()
        summary = tracker.summary()
        assert summary["turns"] == 0
        assert summary["avg_total_ms"] is None

    def test_turn_count_increments(self):
        tracker = LatencyTracker()
        tracker.on_speech_end()
        tracker.on_llm_first_token()
        tracker.on_tts_first_audio()
        tracker.log_turn()

        tracker.on_speech_end()
        tracker.on_llm_first_token()
        tracker.on_tts_first_audio()
        tracker.log_turn()

        summary = tracker.summary()
        assert summary["turns"] == 2

    def test_no_crash_on_missing_steps(self):
        """Calling steps out of order should not raise exceptions."""
        tracker = LatencyTracker()
        # Call log_turn without starting a turn — should be safe
        tracker.log_turn()  # no _current, should be a no-op
        tracker.on_llm_first_token()  # no _current, should be a no-op

    def test_summary_averages_correctly(self):
        """Verify avg_total_ms is the arithmetic mean of completed turns."""
        tracker = LatencyTracker()

        # Manually inject two turns with known latencies
        from logger import TurnLatency

        t1 = TurnLatency(turn_id=1)
        t1.user_speech_end_ts = 0.0
        t1.llm_first_token_ts = 0.4
        t1.tts_first_audio_ts = 0.8  # 800ms total

        t2 = TurnLatency(turn_id=2)
        t2.user_speech_end_ts = 0.0
        t2.llm_first_token_ts = 0.3
        t2.tts_first_audio_ts = 0.6  # 600ms total

        tracker._history = [t1, t2]

        summary = tracker.summary()
        assert summary["turns"] == 2
        assert summary["avg_total_ms"] == 700.0  # (800 + 600) / 2
        assert summary["min_total_ms"] == 600.0
        assert summary["max_total_ms"] == 800.0

    def test_realistic_timing_flow(self):
        """Integration test: simulate a real turn with actual time.perf_counter."""
        tracker = LatencyTracker()

        tracker.on_speech_end()
        time.sleep(0.05)  # ~50ms simulated LLM latency
        tracker.on_llm_first_token()
        time.sleep(0.03)  # ~30ms simulated TTS latency
        tracker.on_tts_first_audio()
        tracker.log_turn()

        summary = tracker.summary()
        assert summary["turns"] == 1
        # Total should be roughly 80ms — allow generous tolerance for CI
        assert 50 <= summary["avg_total_ms"] <= 500, (
            f"Expected ~80ms total latency, got {summary['avg_total_ms']}ms"
        )
