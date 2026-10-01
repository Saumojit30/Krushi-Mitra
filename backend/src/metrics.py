"""
Krushi Mitra — Production Telemetry & Observability
Provides centralized latency metrics tracking, stage timings, and container health probes.
"""

import logging
import os
import time
from typing import Any

from cache import telemetry_cache
from logger import LatencyTracker, TurnLatency

app_logger = logging.getLogger("krushi_mitra.metrics")


class ProductionMetricsCollector:
    """
    Collects performance statistics across voice agent sessions.
    """

    def __init__(self):
        self._tool_call_times: list[dict[str, Any]] = []

    def record_tool_latency(
        self, tool_name: str, duration_ms: float, success: bool = True
    ):
        self._tool_call_times.append(
            {
                "tool": tool_name,
                "duration_ms": duration_ms,
                "success": success,
                "timestamp": time.time(),
            }
        )
        app_logger.info(
            "Tool %s finished in %.1fms (success=%s)",
            tool_name,
            duration_ms,
            success,
        )

    def get_summary(self) -> dict[str, Any]:
        if not self._tool_call_times:
            return {"total_tool_calls": 0, "avg_duration_ms": 0.0}
        total = len(self._tool_call_times)
        avg_dur = sum(t["duration_ms"] for t in self._tool_call_times) / total
        return {
            "total_tool_calls": total,
            "avg_duration_ms": round(avg_dur, 1),
            "recent_calls": self._tool_call_times[-5:],
        }


metrics_collector = ProductionMetricsCollector()


async def get_system_health() -> dict[str, Any]:
    """
    Health check probe reporting system readiness, DB status, and active configuration.
    Suitable for container orchestrators (Docker / Railway / Kubernetes).
    """
    from database import init_db

    db_ready = False
    try:
        init_db()
        db_ready = True
    except Exception as e:
        app_logger.error("Health check DB probe error: %s", e)

    cache_items = await telemetry_cache.size()

    return {
        "status": "healthy" if db_ready else "degraded",
        "service": "krushi_mitra_voice_backend",
        "database_connected": db_ready,
        "telemetry_cache_entries": cache_items,
        "stt_provider": os.getenv("STT_PROVIDER", "deepgram").lower(),
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "murf_model": "GEN2",
        "timestamp": time.time(),
    }


__all__ = [
    "LatencyTracker",
    "TurnLatency",
    "get_system_health",
    "metrics_collector",
]
