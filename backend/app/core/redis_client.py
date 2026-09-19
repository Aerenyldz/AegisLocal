"""Redis client with in-memory fallback for local MVP without Redis."""

from __future__ import annotations

import time
from typing import Any

from app.core.config import get_settings

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore


class MemoryStore:
    def __init__(self) -> None:
        self._kv: dict[str, tuple[Any, float | None]] = {}

    def setex(self, key: str, ttl: int, value: Any) -> None:
        self._kv[key] = (value, time.time() + ttl)

    def get(self, key: str) -> Any | None:
        item = self._kv.get(key)
        if item is None:
            return None
        value, expires = item
        if expires is not None and time.time() > expires:
            self._kv.pop(key, None)
            return None
        return value

    def delete(self, key: str) -> None:
        self._kv.pop(key, None)

    def incr(self, key: str) -> int:
        current = self.get(key)
        n = int(current or 0) + 1
        # preserve remaining TTL if present
        item = self._kv.get(key)
        expires = item[1] if item else None
        self._kv[key] = (str(n), expires)
        return n

    def expire(self, key: str, ttl: int) -> None:
        item = self._kv.get(key)
        if item is None:
            return
        value, _ = item
        self._kv[key] = (value, time.time() + ttl)


_memory = MemoryStore()
_redis = None


def get_store():
    global _redis
    settings = get_settings()
    if not settings.redis_enabled or redis is None:
        return _memory
    if _redis is None:
        _redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis
