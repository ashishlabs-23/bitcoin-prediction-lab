"""
Token Bucket Rate Limiter
=========================
Protects FastAPI inference and WebSocket routes from burst overload.

Fix notes (2026-11-28):
- ``self.tokens`` was an unbounded dict (one entry per client forever -> memory
  leak on long-running deployments). It is now swept periodically and capped.
- No synchronisation -> torn reads under multiple threads/workers. All state
  mutation now happens under a ``threading.Lock``.
- ``Tuple[float, float]`` used as a mutable bucket record replaced by a small
  dataclass with an explicit ``last_seen`` for eviction decisions.
The public surface (``RateLimiter.is_allowed``, module-level ``rate_limiter``)
is unchanged.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(slots=True)
class _Bucket:
    tokens: float
    last_refill: float
    last_seen: float


class RateLimiter:
    """Thread-safe token bucket with bounded memory."""

    def __init__(
        self,
        requests_per_minute: int = 120,
        max_tracked_clients: int = 10_000,
        idle_ttl_seconds: float = 900.0,
        sweep_interval_seconds: float = 60.0,
    ) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        if max_tracked_clients <= 0:
            raise ValueError("max_tracked_clients must be positive")

        self.rate = requests_per_minute / 60.0
        self.capacity = float(requests_per_minute)
        self.tokens: Dict[str, _Bucket] = {}
        self.max_tracked_clients = max_tracked_clients
        self.idle_ttl_seconds = idle_ttl_seconds
        self.sweep_interval_seconds = sweep_interval_seconds
        self._lock = threading.Lock()
        self._last_sweep = time.monotonic()

    # -- internal -----------------------------------------------------------

    def _sweep_locked(self, now: float) -> None:
        """Drop idle buckets, then enforce the hard cap. Caller holds the lock."""
        if now - self._last_sweep < self.sweep_interval_seconds:
            return
        self._last_sweep = now

        cutoff = now - self.idle_ttl_seconds
        for key in [k for k, b in self.tokens.items() if b.last_seen < cutoff]:
            del self.tokens[key]

        overflow = len(self.tokens) - self.max_tracked_clients
        if overflow > 0:
            for key, _ in sorted(self.tokens.items(), key=lambda kv: kv[1].last_seen)[:overflow]:
                del self.tokens[key]

    def _refill(self, bucket: _Bucket, now: float) -> None:
        elapsed = max(0.0, now - bucket.last_refill)
        bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.rate)
        bucket.last_refill = now
        bucket.last_seen = now

    # -- public API ---------------------------------------------------------

    def is_allowed(self, client_id: str) -> bool:
        """Consume one token for ``client_id``. Returns False when throttled."""
        now = time.monotonic()
        with self._lock:
            self._sweep_locked(now)

            bucket = self.tokens.get(client_id)
            if bucket is None:
                bucket = _Bucket(tokens=self.capacity, last_refill=now, last_seen=now)
                self.tokens[client_id] = bucket
            else:
                self._refill(bucket, now)

            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True
            return False

    def remaining_tokens(self, client_id: str) -> Optional[float]:
        """Introspection helper for tests/metrics."""
        now = time.monotonic()
        with self._lock:
            bucket = self.tokens.get(client_id)
            if bucket is None:
                return None
            self._refill(bucket, now)
            return bucket.tokens

    def tracked_clients(self) -> int:
        """Number of client identities currently held in memory."""
        with self._lock:
            return len(self.tokens)


rate_limiter = RateLimiter(requests_per_minute=120)
