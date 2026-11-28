"""Regression tests for the 2026-11-28 hardening pass.

Each test pins a specific defect that was found and fixed, so it cannot come
back silently:

* the readiness cache that was never populated (5.3 s /health);
* absolute server paths leaking through gate failure reasons;
* the dashboard rebuilding on every request instead of serving a cache;
* derivative feed failures reported as a generic exception name;
* the rate limiter growing without bound.
"""
from __future__ import annotations

import re
import threading

import httpx
import pytest
from fastapi.testclient import TestClient

import api.market_drivers as market_drivers
from api.server import app
from validation.startup_gate import _redact_paths


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Gate failure reasons must not disclose the server's filesystem layout.
# ---------------------------------------------------------------------------
def test_redact_paths_strips_posix_and_windows_paths():
    raw = (
        "Manifest  : /home/ubuntu/bt/experiments/results/freeze/har.json\n"
        "  \u2717 FAIL   Python version (minor)\n"
        "           frozen=3.13.14, live=3.12.3\n"
        "  [FAIL] FREEZE_BROKEN - 1 critical check(s) failed\n"
    )
    out = _redact_paths(raw)

    assert "/home/" not in out
    assert "ubuntu" not in out
    # The actionable detail survives the scrub.
    assert "Python version" in out
    assert "3.12.3" in out


def test_redact_paths_handles_windows_paths_and_empty_input():
    assert "C:\\Users\\" not in _redact_paths("FAIL at C:\\Users\\Ashish\\bt\\manifest.json")
    assert _redact_paths("") == ""
    assert _redact_paths(None) == ""


def test_redact_paths_caps_length():
    assert len(_redact_paths("FAIL " + "x" * 5000, limit=200)) <= 200


# ---------------------------------------------------------------------------
# /health is a liveness probe: fast, path-free, and explicit about the gate.
# ---------------------------------------------------------------------------
def test_health_is_fast_and_does_not_leak_paths(client):
    import time

    started = time.perf_counter()
    resp = client.get("/health")
    elapsed = time.perf_counter() - started

    assert resp.status_code == 200
    assert elapsed < 2.0, f"/health took {elapsed:.2f}s; the readiness cache is dead again"

    body = resp.text
    assert "/home/" not in body and "C:\\Users\\" not in body
    payload = resp.json()
    assert "research_reason_code" in payload
    assert payload["trading_enabled"] is False


def test_health_reports_gate_reason_code(client):
    payload = client.get("/health").json()
    assert payload["research_authorized"] is False or payload["research_status"] == "AUTHORIZED_FOR_PRODUCTION"
    if not payload["research_authorized"]:
        assert payload["research_reason_code"] not in (None, "NONE")


# ---------------------------------------------------------------------------
# Dashboard cache: repeated calls must not rebuild the payload.
# ---------------------------------------------------------------------------
def test_dashboard_cache_is_used_within_ttl(client, monkeypatch):
    import api.market_monitor_routes as routes

    calls = {"n": 0}
    real_build = routes._build_dashboard

    async def counting_build(request, horizon="24h"):
        calls["n"] += 1
        return await real_build(request, horizon)

    monkeypatch.setattr(routes, "_build_dashboard", counting_build)
    monkeypatch.setattr(routes, "_DASH_TTL", 60.0)
    routes._DASH_CACHE.clear()

    first = client.get("/api/dashboard?horizon=24h")
    second = client.get("/api/dashboard?horizon=24h")

    assert first.status_code == second.status_code == 200
    assert calls["n"] == 1, f"dashboard rebuilt {calls['n']} times; the cache is not being used"
    routes._DASH_CACHE.clear()


def test_dashboard_payload_keeps_governance_flags(client):
    payload = client.get("/api/dashboard?horizon=24h").json()
    research = payload["research"]
    assert research["trading_enabled"] is False
    assert research["production_forecast_available"] is False or research["production_model"] != "BLOCKED"


# ---------------------------------------------------------------------------
# Derivative feed failures carry an actionable reason.
# ---------------------------------------------------------------------------
def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://fapi.binance.com/fapi/v1/premiumIndex")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


@pytest.mark.parametrize(
    "status, expected",
    [(451, "HTTP_451_RESTRICTED_LOCATION"), (429, "HTTP_429_RATE_LIMITED"), (503, "HTTP_503")],
)
def test_derivative_failures_name_the_http_status(monkeypatch, status, expected):
    async def boom(*_args, **_kwargs):
        raise _http_status_error(status)

    monkeypatch.setattr(market_drivers, "_get_json", boom)
    monkeypatch.setattr(market_drivers, "_DERIVATIVE_CACHE", None, raising=False)

    result = __import__("asyncio").run(market_drivers._fetch_derivatives(client=None))

    assert result["status"] == "UNAVAILABLE"
    assert result["reason"] == expected
    assert result["http_status"] == status


# ---------------------------------------------------------------------------
# Rate limiter stays bounded under load.
# ---------------------------------------------------------------------------
def test_rate_limiter_is_bounded_and_thread_safe():
    from api.rate_limiter import RateLimiter

    limiter = RateLimiter(requests_per_minute=600, max_tracked_clients=50)
    errors = []

    def hammer(idx: int) -> None:
        try:
            for _ in range(20):
                limiter.is_allowed(f"key-{idx}")
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=hammer, args=(i,)) for i in range(40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert limiter.tracked_clients() <= 50


def test_versioned_assets_are_cached_immutably(client):
    resp = client.get("/app.js?v=99.0.0")
    if resp.status_code != 200:
        pytest.skip("static assets not mounted in this environment")
    assert "immutable" in resp.headers.get("cache-control", "")
    assert re.search(r"max-age=\d+", resp.headers.get("cache-control", ""))


def test_research_report_integrity_manifest_is_in_sync():
    """Every allowlisted research report must match its pinned SHA256.

    Six reports had silently drifted from the pinned hashes (the reports were
    regenerated in an earlier commit but the manifest was not), which made
    /api/research/results report INTEGRITY_MISMATCH for perfectly good files.
    scripts/sync_research_report_hashes.py is the documented repair path.
    """
    import importlib.util
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "sync_research_report_hashes",
        repo_root / "scripts" / "sync_research_report_hashes.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main([]) == 0
