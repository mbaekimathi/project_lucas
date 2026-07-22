"""
Shared process/cross-process cache helpers.

Uses Redis when REDIS_URL (or REDIS_HOST) is configured; otherwise falls back
to an in-process memory store (same behaviour as before Phase 2).
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Optional

_mem_lock = threading.Lock()
_mem: dict[str, tuple[Any, float]] = {}

_redis_client = None
_redis_tried = False
_redis_lock = threading.Lock()


def redis_enabled() -> bool:
    return bool(
        (os.environ.get('REDIS_URL') or '').strip()
        or (os.environ.get('REDIS_HOST') or '').strip()
    )


def get_redis():
    """Return a Redis client or None. Safe to call repeatedly."""
    global _redis_client, _redis_tried
    if _redis_tried:
        return _redis_client
    with _redis_lock:
        if _redis_tried:
            return _redis_client
        _redis_tried = True
        if not redis_enabled():
            return None
        try:
            import redis  # type: ignore
        except ImportError:
            print('shared_cache: redis package not installed — using memory fallback')
            return None
        try:
            url = (os.environ.get('REDIS_URL') or '').strip()
            if url:
                _redis_client = redis.from_url(url, decode_responses=True, socket_connect_timeout=1.5)
            else:
                host = (os.environ.get('REDIS_HOST') or '127.0.0.1').strip()
                port = int(os.environ.get('REDIS_PORT', '6379'))
                db = int(os.environ.get('REDIS_DB', '0'))
                password = os.environ.get('REDIS_PASSWORD') or None
                _redis_client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=True,
                    socket_connect_timeout=1.5,
                )
            _redis_client.ping()
        except Exception as e:
            print(f'shared_cache: Redis unavailable ({e}) — using memory fallback')
            _redis_client = None
        return _redis_client


def cache_get(key: str) -> Optional[Any]:
    r = get_redis()
    if r is not None:
        try:
            raw = r.get(f'ec:{key}')
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            pass
    now = time.monotonic()
    with _mem_lock:
        item = _mem.get(key)
        if not item:
            return None
        value, expires = item
        if expires and now >= expires:
            _mem.pop(key, None)
            return None
        return value


def cache_set(key: str, value: Any, ttl_sec: int = 300) -> None:
    ttl = max(1, int(ttl_sec))
    r = get_redis()
    if r is not None:
        try:
            r.setex(f'ec:{key}', ttl, json.dumps(value, default=str))
            return
        except Exception:
            pass
    with _mem_lock:
        _mem[key] = (value, time.monotonic() + ttl)


def cache_delete(key: str) -> None:
    r = get_redis()
    if r is not None:
        try:
            r.delete(f'ec:{key}')
        except Exception:
            pass
    with _mem_lock:
        _mem.pop(key, None)


def rate_limit_hit(scope_key: str, limit: int, window_sec: int) -> tuple[bool, Optional[int]]:
    """
    Fixed-window rate limit.
    Returns (allowed, retry_after_seconds|None).
    Prefers Redis INCR+EXPIRE; falls back to memory timestamps.
    """
    limit = max(1, int(limit))
    window_sec = max(1, int(window_sec))
    r = get_redis()
    if r is not None:
        key = f'ec:rl:{scope_key}'
        try:
            count = r.incr(key)
            if count == 1:
                r.expire(key, window_sec)
            if count > limit:
                ttl = r.ttl(key)
                retry = int(ttl) if ttl and ttl > 0 else window_sec
                return False, max(1, min(retry, window_sec))
            return True, None
        except Exception:
            pass

    now = time.time()
    bucket_key = f'rl:{scope_key}'
    with _mem_lock:
        raw = _mem.get(bucket_key)
        hits = list(raw[0]) if raw else []
        hits = [t for t in hits if now - t < window_sec]
        if len(hits) >= limit:
            retry = int(window_sec - (now - hits[0])) + 1
            _mem[bucket_key] = (hits, time.monotonic() + window_sec)
            return False, max(1, min(retry, window_sec))
        hits.append(now)
        _mem[bucket_key] = (hits, time.monotonic() + window_sec)
    return True, None
