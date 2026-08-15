"""
Krushi Mitra — Latency Logger
Tracks end-of-speech to first-audio latency per conversation turn.
Required for production observability — Day 1 challenge advanced task.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("krushi_mitra.latency")


@dataclass
class TurnLatency:
    turn_id: int
    user_speech_end_ts: float = 0.0
    llm_first_token_ts: float = 0.0
    tts_first_audio_ts: float = 0.0

    @property
    def llm_latency_ms(self) -> Optional[float]:
        if self.user_speech_end_ts is not None and self.llm_first_token_ts:
            return round((self.llm_first_token_ts - self.user_speech_end_ts) * 1000, 1)
        return None

    @property
    def tts_latency_ms(self) -> Optional[float]:
        if self.llm_first_token_ts is not None and self.tts_first_audio_ts:
            return round((self.tts_first_audio_ts - self.llm_first_token_ts) * 1000, 1)
        return None

    @property
    def total_latency_ms(self) -> Optional[float]:
        if self.user_speech_end_ts is not None and self.tts_first_audio_ts:
            return round((self.tts_first_audio_ts - self.user_speech_end_ts) * 1000, 1)
        return None


class LatencyTracker:
    """
    Tracks per-turn latency for the Krushi Mitra voice agent.
    Records the critical pipeline: end-of-speech → LLM first token → TTS first audio.

    Usage:
        tracker = LatencyTracker()
        tracker.on_speech_end()
        tracker.on_llm_first_token()
        tracker.on_tts_first_audio()
        tracker.log_turn()
    """

    def __init__(self):
        self._turn_count: int = 0
        self._current: Optional[TurnLatency] = None
        self._history: list[TurnLatency] = []

    def on_speech_end(self) -> None:
        """Call when the user stops speaking (VAD end-of-utterance)."""
        self._turn_count += 1
        self._current = TurnLatency(turn_id=self._turn_count)
        self._current.user_speech_end_ts = time.perf_counter()

    def on_llm_first_token(self) -> None:
        """Call when the LLM produces its first output token."""
        if self._current:
            self._current.llm_first_token_ts = time.perf_counter()

    def on_tts_first_audio(self) -> None:
        """Call when Murf Falcon sends back the first audio chunk."""
        if self._current:
            self._current.tts_first_audio_ts = time.perf_counter()

    def log_turn(self) -> None:
        """Log the completed turn's latency breakdown."""
        if not self._current:
            return
        turn = self._current
        self._history.append(turn)
        self._current = None

        logger.info(
            "[LATENCY] turn=%d | speech→llm=%s ms | llm→tts=%s ms | total=%s ms",
            turn.turn_id,
            turn.llm_latency_ms,
            turn.tts_latency_ms,
            turn.total_latency_ms,
        )

    def summary(self) -> dict:
        """Return a summary of all recorded turns."""
        completed = [t for t in self._history if t.total_latency_ms is not None]
        if not completed:
            return {"turns": 0, "avg_total_ms": None}

        avg_total = round(
            sum(t.total_latency_ms for t in completed) / len(completed), 1
        )
        return {
            "turns": len(completed),
            "avg_total_ms": avg_total,
            "min_total_ms": min(t.total_latency_ms for t in completed),
            "max_total_ms": max(t.total_latency_ms for t in completed),
        }
