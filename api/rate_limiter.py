"""
Token Bucket Rate Limiter
=========================
Protects FastAPI inference and WebSocket routes from burst overload.
"""

import time
from typing import Dict, Tuple


class RateLimiter:
    def __init__(self, requests_per_minute: int = 120):
        self.rate = requests_per_minute / 60.0
        self.capacity = requests_per_minute
        self.tokens: Dict[str, Tuple[float, float]] = {}

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        if client_id not in self.tokens:
            self.tokens[client_id] = (self.capacity - 1, now)
            return True

        current_tokens, last_update = self.tokens[client_id]
        elapsed = now - last_update
        current_tokens = min(self.capacity, current_tokens + elapsed * self.rate)

        if current_tokens >= 1.0:
            self.tokens[client_id] = (current_tokens - 1.0, now)
            return True
        else:
            self.tokens[client_id] = (current_tokens, now)
            return False


rate_limiter = RateLimiter(requests_per_minute=120)
