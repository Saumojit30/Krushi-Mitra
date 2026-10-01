"""
Async TTL Cache Utility
Provides fast in-memory caching with time-to-live expiration to prevent
external API rate-limiting and eliminate network latency on hot repeated queries.
"""

import asyncio
import time
from typing import Any, Optional


class AsyncTTLCache:
    """
    Thread-safe asynchronous in-memory TTL (Time-To-Live) cache.
    """

    def __init__(self, default_ttl_seconds: int = 1800):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl_seconds
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a value if present and not expired."""
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._cache[key]
                return None
            return value

    async def set(
        self, key: str, value: Any, ttl_seconds: Optional[int] = None
    ) -> None:
        """Store a value with a specific or default TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expires_at = time.monotonic() + ttl
        async with self._lock:
            self._cache[key] = (value, expires_at)

    async def clear(self) -> None:
        """Clear all cached entries."""
        async with self._lock:
            self._cache.clear()

    async def size(self) -> int:
        """Return count of unexpired items."""
        now = time.monotonic()
        async with self._lock:
            return sum(1 for _, expires_at in self._cache.values() if expires_at > now)


# Global instances for agricultural telemetry
telemetry_cache = AsyncTTLCache(
    default_ttl_seconds=1800
)  # 30-minute TTL for weather/soil
