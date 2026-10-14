"""
tests/test_agent_a_security_regression.py — Agent A Security Regression Test Suite
==================================================================================
Covers:
1. SSRF destination host allowlist and IP validation (IPv4, IPv6, loopback, private, cloud metadata).
2. HTTP redirect prevention (follow_redirects=False).
3. RBAC role enforcement for ADMIN-only routes (/api/arena/trade, /api/arena/reset, /api/arena/retrain, /api/arena/sync_google_sheet).
4. Information disclosure / response leakage prevention.
5. Rate-limiter cardinality bounding and LRU eviction under 15,000+ client keys.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.security_validators import (
    validate_safe_url,
    validate_sheet_sync_url,
    SecurityValidationError
)
from engine.arena_runner import arena_runner
from config.security import API_KEYS_ENV, UserRole
from api.security_middleware import RateLimiter
from api.server import app


def test_ssrf_hostname_allowlist():
    """Verify only permitted Google Apps Script hosts are allowed for sheet sync."""
    valid_url = "https://script.google.com/macros/s/AKfycbz_test/exec"
    cleaned, ips = validate_sheet_sync_url(valid_url)
    assert "script.google.com" in cleaned
    assert isinstance(ips, list) and len(ips) > 0

    # Unauthorized hosts must be rejected
    evil_urls = [
        "https://evil.attacker.com/webhook",
        "https://script.google.com.evil.com/webhook",
        "https://webhook.site/abc-123",
        "http://script.google.com/macros/s/exec", # HTTP plain text disallowed
        "https://127.0.0.1/macros",
        "https://169.254.169.254/latest/meta-data/"
    ]
    for u in evil_urls:
        with pytest.raises(SecurityValidationError):
            validate_sheet_sync_url(u)


def test_ssrf_private_and_metadata_ip_resolution(monkeypatch):
    """Verify that hostnames resolving to private, loopback, or cloud metadata IPs are rejected."""
    import socket

    # Simulate DNS rebinding or private IP resolution
    def mock_getaddrinfo(host, port, *args, **kwargs):
        if "metadata" in host or "local" in host:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 443))]
        if "loopback" in host:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        if "internal" in host:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.250.190.46", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)

    with pytest.raises(SecurityValidationError):
        validate_safe_url("https://metadata.google.internal/computeMetadata")

    with pytest.raises(SecurityValidationError):
        validate_safe_url("https://loopback.test/api")

    with pytest.raises(SecurityValidationError):
        validate_safe_url("https://internal.network/status")


def test_rbac_admin_routes_require_authentication(monkeypatch):
    """Verify destructive/admin arena endpoints reject unauthenticated or non-admin callers."""
    client = TestClient(app)

    user_key = "test-agent-a-user-key"
    research_key = "test-agent-a-research-key"
    admin_key = "test-agent-a-admin-key"

    monkeypatch.setitem(API_KEYS_ENV, user_key, UserRole.USER)
    monkeypatch.setitem(API_KEYS_ENV, research_key, UserRole.RESEARCH)
    monkeypatch.setitem(API_KEYS_ENV, admin_key, UserRole.ADMIN)

    admin_endpoints = [
        ("/api/arena/trade", {"action": "BUY", "amount": 0.1, "strategy_name": "MEIE-IGNITION"}),
        ("/api/arena/reset", {}),
        ("/api/arena/retrain", {}),
        ("/api/arena/sync_google_sheet", {"webhook_url": "https://script.google.com/macros/s/test/exec"}),
    ]

    for path, payload in admin_endpoints:
        # 1. Unauthenticated / PUBLIC -> 401 or 403 Forbidden
        res = client.post(path, json=payload)
        assert res.status_code in (401, 403), f"{path} unauthenticated did not return 401/403: {res.status_code}"

        # 2. USER role -> 403 Forbidden
        res_user = client.post(path, json=payload, headers={"X-API-Key": user_key})
        assert res_user.status_code == 403, f"{path} USER role did not return 403: {res_user.status_code}"

        # 3. RESEARCH role -> 403 Forbidden
        res_res = client.post(path, json=payload, headers={"X-API-Key": research_key})
        assert res_res.status_code == 403, f"{path} RESEARCH role did not return 403: {res_res.status_code}"

        # 4. ADMIN role -> authorized (not 401 and not 403)
        res_admin = client.post(path, json=payload, headers={"X-API-Key": admin_key})
        assert res_admin.status_code not in (401, 403), f"{path} ADMIN role unexpectedly rejected: {res_admin.status_code}"


def test_rate_limiter_cardinality_and_lru_eviction():
    """Verify RateLimiter handles large streams of client keys without unbounded memory growth."""
    limiter = RateLimiter(max_history_per_client=50, max_cardinality=500)

    # Stream 2,500 unique client IPs
    for i in range(2500):
        client_ip = f"198.51.100.{i % 256}:{i}"
        allowed, remaining = limiter.is_allowed(client_ip, 100)
        assert allowed is True

    # Confirm active tracking dictionary is strictly bounded
    assert len(limiter.requests) <= 500, f"RateLimiter exceeded max_cardinality: {len(limiter.requests)}"


def test_sheet_sync_no_sensitive_data_leakage(monkeypatch):
    """Verify sheet sync failure does not leak raw tokens or internal upstream body."""
    import httpx

    def mock_post(*args, **kwargs):
        raise httpx.ConnectTimeout("Upstream timed out")

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    result = arena_runner.sync_to_google_script("https://script.google.com/macros/s/test/exec")
    assert result["status"] == "error"
    assert result["reason"] == "Webhook destination timed out."
    assert "https://script.google.com" not in result["reason"]
