"""
tests/test_rate_limit_scope.py — Tests for Rate Limiter Scope and Tier Enforcement
==================================================================================
Verifies:
- Sliding-window rate limiter records timestamps per client.
- Rate limits exist for all defined UserRole tiers.
"""

from config.security import UserRole, RATE_LIMITS
from api.security_middleware import RateLimiter

def test_rate_limits_defined_for_all_roles():
    for role in [UserRole.PUBLIC, UserRole.USER, UserRole.RESEARCH, UserRole.ADMIN]:
        assert role in RATE_LIMITS
        assert RATE_LIMITS[role] > 0

def test_rate_limiter_sliding_window_allows_within_budget():
    limiter = RateLimiter()
    key = "test-client-127.0.0.1:USER"
    # First request should be allowed
    allowed, remaining = limiter.is_allowed(key, limit_per_minute=5)
    assert allowed is True
    assert remaining == 4
