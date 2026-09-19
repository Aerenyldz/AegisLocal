"""Sliding-window rate limiter (Redis or in-memory)."""

from __future__ import annotations

import time

from app.core.config import get_settings
from app.core.redis_client import get_store


def check_rate_limit(key: str) -> tuple[bool, int]:
    """
    Returns (allowed, remaining).
    Key typically: client IP or session id.
    """
    settings = get_settings()
    store = get_store()
    window = settings.rate_limit_window_seconds
    limit = settings.rate_limit_max_requests
    bucket = f"rl:{key}:{int(time.time() // window)}"

    count = store.incr(bucket)
    if count == 1:
        store.expire(bucket, window + 1)

    remaining = max(0, limit - int(count))
    return int(count) <= limit, remaining
