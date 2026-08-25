"""
tests/test_deployment_config.py — Tests for Production Security Configuration
=============================================================================
Verifies:
- Production kill switches are locked.
- Security headers configuration contains HSTS, CSP, and X-Frame-Options.
- Allowed external domains are whitelisted.
"""

from config.security import (
    TRADING_ENABLED,
    PRODUCTION_MODEL_FROZEN,
    PUBLIC_DATABASE_ACCESS,
    PUBLIC_SHELL_ACCESS,
    SECURITY_HEADERS,
    ALLOWED_EXTERNAL_DOMAINS
)

def test_production_kill_switches_locked():
    assert TRADING_ENABLED is False
    assert PRODUCTION_MODEL_FROZEN is True
    assert PUBLIC_DATABASE_ACCESS is False
    assert PUBLIC_SHELL_ACCESS is False

def test_security_headers_configured():
    assert "Strict-Transport-Security" in SECURITY_HEADERS
    assert "Content-Security-Policy" in SECURITY_HEADERS
    assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"
    assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"

def test_allowed_external_domains():
    assert "api.binance.com" in ALLOWED_EXTERNAL_DOMAINS
    assert "api.coinmetrics.io" in ALLOWED_EXTERNAL_DOMAINS
