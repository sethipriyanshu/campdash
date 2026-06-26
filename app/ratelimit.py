"""Tiny in-process sliding-window rate limiter (single-worker event use). Move to Redis if you
run multiple workers."""
from __future__ import annotations

import time
from collections import defaultdict

_hits: dict[str, list[float]] = defaultdict(list)


def allow(key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    cutoff = now - window_seconds
    recent = [t for t in _hits[key] if t > cutoff]
    if len(recent) >= limit:
        _hits[key] = recent
        return False
    recent.append(now)
    _hits[key] = recent
    return True
