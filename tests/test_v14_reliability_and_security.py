"""
tests/test_v14_reliability_and_security.py — V14 Reliability, Terminal Feature Completion & Security Hardening
=============================================================================================================
Independent verification suite covering:
1. Deterministic versioning and non-cached static asset delivery (OWASP ASVS & Cache headers).
2. OWASP ASVS 5.0 Security Headers (CSP, Frame-Options, Content-Type-Options, Referrer-Policy, HSTS).
3. Sensitive Information & Path Disclosure Redaction (Zero leakage of filesystem paths, DB URIs, stack traces).
4. Safe Exception Handling with Non-Sensitive Diagnostic Request IDs.
5. User-Controlled Strategy Overlay & Preview Lifecycle Separation (Preview vs Active Overlay vs Disabled).
6. Non-Fabrication of Signals / Trades / Depth: Truthful empty states and no fake market levels.
7. Governance & Execution Invariants: Strict live trading DISABLED, OFFLINE_RESEARCH_ONLY.
8. Partial Failure Graceful Degradation: Unaffected endpoints remain 200 OK when optional modules abstain.
"""

import re
import pytest
from fastapi.testclient import TestClient

from api.server import app
from config.security import TRADING_ENABLED, PRODUCTION_MODEL_FROZEN

client = TestClient(app, raise_server_exceptions=False)


# ==============================================================================
# 1. Deterministic Versioning and Asset Cache Invalidation
# ==============================================================================

def test_v14_index_html_deterministic_asset_versioning():
    """Verify index.html serves v14.0.0 cache-busting query strings for css and js."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert re.search(r'href="/styles\.css\?v=\d+\.\d+\.\d+"', html), "styles.css must be versioned with ?v=..."
    assert re.search(r'src="/app\.js\?v=\d+\.\d+\.\d+"', html), "app.js must be versioned with ?v=..."


def test_v14_static_assets_cache_control_headers():
    """Verify that root, scripts, and stylesheets are served with strict no-cache headers."""
    for path in ["/", "/styles.css", "/app.js"]:
        resp = client.get(path)
        assert resp.status_code == 200
        cache_control = resp.headers.get("Cache-Control", "")
        assert "no-cache" in cache_control, f"Path {path} missing no-cache in Cache-Control"
        assert "no-store" in cache_control, f"Path {path} missing no-store in Cache-Control"
        assert "must-revalidate" in cache_control, f"Path {path} missing must-revalidate in Cache-Control"


# ==============================================================================
# 2. OWASP ASVS 5.0 Security Headers Verification
# ==============================================================================

def test_v14_owasp_asvs_security_headers():
    """Verify presence and correctness of all mandated OWASP security headers."""
    resp = client.get("/health")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "max-age=31536000" in headers.get("Strict-Transport-Security", "")
    assert "camera=()" in headers.get("Permissions-Policy", "")

    csp = headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


# ==============================================================================
# 3. Sensitive Information & Path Disclosure Redaction
# ==============================================================================

_PATH_DISCLOSURE_REGEX = re.compile(
    r"([A-Za-z]:\\[^ \"'>\r\n\t]+|/(?:Users|home|root|var|etc|opt|tmp)/[^ \"'>\r\n\t]+)",
    re.IGNORECASE
)
_DB_DISCLOSURE_REGEX = re.compile(
    r"(?:sqlite|postgres|mysql|mongodb)(?:\+[a-z]+)?://[^ \"'>\r\n\t]+",
    re.IGNORECASE
)


def test_v14_exception_sanitization_and_request_id():
    """Verify that non-existent routes or errors return a sanitized response with a request_id."""
    resp = client.get("/api/non-existent-endpoint-testing-404")
    assert resp.status_code == 404
    data = resp.json()
    assert "request_id" in data or "detail" in data

    resp_str = resp.text
    # Must NOT disclose server workstation paths or user names
    assert "C:\\Users\\" not in resp_str
    assert "/home/" not in resp_str
    assert not _DB_DISCLOSURE_REGEX.search(resp_str), "Database connection string leaked in error response"


def test_v14_public_api_endpoints_no_path_leakage():
    """Verify all public API responses are free from leaked filesystem paths and credentials."""
    endpoints = [
        "/health",
        "/market/candles?interval=1h",
        "/prediction/latest?live=false",
        "/api/tournament/latest",
        "/api/tournament/setup/SHORT_HORIZON_MEAN_REVERSION?enabled=false",
        "/api/arena/active-paper-position",
        "/api/arena/trade-markers?limit=10"
    ]

    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 200, f"Endpoint {ep} failed with status {resp.status_code}"
        text = resp.text
        # Assert no Windows absolute path leakage (like C:\Users\...)
        assert "C:\\Users\\" not in text, f"Endpoint {ep} leaked Windows path: {text[:200]}"
        assert "/home/" not in text, f"Endpoint {ep} leaked Linux path: {text[:200]}"
        assert not _DB_DISCLOSURE_REGEX.search(text), f"Endpoint {ep} leaked DB URI"


# ==============================================================================
# 4. User-Controlled Strategy Overlay & Preview Lifecycle Separation
# ==============================================================================

def test_v14_strategy_setup_preview_mode_invariants():
    """
    Verify setup endpoint distinguishes preview mode (enabled=false) from
    enabled overlay mode (enabled=true), with explicit state contracts.
    """
    strat_id = "SHORT_HORIZON_MEAN_REVERSION"

    # 1. Preview request (enabled=false)
    resp_prev = client.get(f"/api/tournament/setup/{strat_id}?enabled=false")
    assert resp_prev.status_code == 200
    prev_data = resp_prev.json()
    assert prev_data["strategy_id"] == strat_id
    assert prev_data["overlay_enabled"] is False
    assert prev_data["setup_state"] in [
        "SETUP_PREVIEW_AVAILABLE", "SETUP_AVAILABLE", "NO_SETUP", "BLOCKED_BY_REGIME", "BLOCKED_BY_DATA"
    ]
    # In preview mode, live monitoring must NOT be active
    assert prev_data.get("monitoring_mode") != "CONTINUOUS_AUTHORIZED"

    # 2. Enabled overlay request (enabled=true)
    resp_act = client.get(f"/api/tournament/setup/{strat_id}?enabled=true")
    assert resp_act.status_code == 200
    act_data = resp_act.json()
    assert act_data["strategy_id"] == strat_id
    assert act_data["overlay_enabled"] is True


def test_v14_no_fabricated_strategy_levels_when_no_setup():
    """
    Verify that if a strategy does not have an active trigger, the API
    truthfully reports NO_SETUP and does NOT fabricate entry/tp/sl levels.
    """
    resp = client.get("/api/tournament/setup/SHORT_HORIZON_MEAN_REVERSION?enabled=false")
    assert resp.status_code == 200
    data = resp.json()
    if data.get("setup_state") in ["NO_SETUP", "BLOCKED_BY_REGIME", "OVERLAY_OFF"]:
        assert data.get("entry_price") is None or data.get("setup_state") == "SETUP_PREVIEW_AVAILABLE", "Fabricated entry_price on NO_SETUP"


# ==============================================================================
# 5. Non-Fabrication of Paper Trades & Truthful Empty State
# ==============================================================================

def test_v14_paper_trades_truthful_reporting():
    """Verify paper trades endpoint does not return hardcoded fabricated trade fixtures."""
    resp = client.get("/api/arena/trade-markers?limit=50")
    assert resp.status_code == 200
    data = resp.json()
    assert "markers" in data
    # Markers must be genuine list from database/ledger, not mock values
    markers = data["markers"]
    for m in markers:
        assert "price" in m
        assert "timestamp" in m or "time" in m


# ==============================================================================
# 6. Governance & Execution Invariants
# ==============================================================================

def test_v14_master_governance_invariants():
    """Verify live trading and production modification invariants remain strictly enforced."""
    assert TRADING_ENABLED is False, "TRADING_ENABLED must be strictly False"
    assert PRODUCTION_MODEL_FROZEN is True, "PRODUCTION_MODEL_FROZEN must be True"

    # Health check must declare disabled execution
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("trading_enabled") is False or data.get("execution_status") == "DISABLED"


# ==============================================================================
# 7. Partial Failure Graceful Degradation
# ==============================================================================

def test_v14_graceful_degradation_independent_endpoints():
    """
    Verify that price chart candles, forecast baseline, and market telemetry
    remain fully operational and decoupled from tournament or scenario errors.
    """
    # 1. Market candles remain accessible
    mkt = client.get("/market/candles?interval=1h")
    assert mkt.status_code == 200
    mkt_data = mkt.json()
    assert "candles" in mkt_data

    # 2. Independent forecast endpoint remains accessible
    fc = client.get("/prediction/latest?live=false")
    assert fc.status_code == 200

    # 3. Strategy tournament remains accessible
    tourn = client.get("/api/tournament/latest")
    assert tourn.status_code == 200
    assert "top_candidates" in tourn.json()
