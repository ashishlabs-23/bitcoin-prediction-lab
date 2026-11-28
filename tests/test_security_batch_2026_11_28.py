"""
tests/test_security_batch_2026_11_28.py — Approved Security Batch (2026-11-28)
==============================================================================
Regression tests for:
1. POST /api/arena/experiment ledger commits are ADMIN-only (non-admin callers
   are downgraded to commit_to_ledger=False instead of being rejected).
2. Streaming (chunked) request bodies are capped by RateLimitingMiddleware.
3. Client-facing JSON no longer echoes raw ``str(e)`` exception text.
4. Fly/Render deployments declare trusted hosts + CORS origins and /health
   still answers for the Fly hostname.
5. AUTH_FAILURE audit logs use a non-reversible token fingerprint.
7. Dockerfile builds on CPython 3.13 (both stages).
"""
import asyncio
import hashlib
import json
import pathlib
import re
import tomllib

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

import api.routes_arena as routes_arena
import api.security_auth as security_auth
from api.security_middleware import (
    MAX_REQUEST_BODY_BYTES,
    RateLimitingMiddleware,
    sanitize_client_error,
)
from api.server import app
from config import security as security_config
from config.security import UserRole

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

VALID_ONCHAIN = {
    "mvrv_ratio": 1.85,
    "nupl": 0.42,
    "cycle_phase": "NEUTRAL",
    "timestamp": "2026-11-28T00:00:00+00:00",
    "source": "pytest",
    "is_live": True,
    "is_degraded": False,
    "influence_weight": 1.0,
    "quality": "VALID",
    "schema_version": "v1.0",
}


@pytest.fixture
def arena_client(monkeypatch):
    """TestClient with the arena experiment dependencies pinned to fixtures."""
    client = TestClient(app, base_url="http://testserver", raise_server_exceptions=False)

    ledger_calls = []

    monkeypatch.setattr(routes_arena, "record_stress_trial", lambda **kwargs: ledger_calls.append(kwargs))
    monkeypatch.setattr(routes_arena.feature_cache, "get_latest_row", lambda: None)
    monkeypatch.setattr(
        routes_arena,
        "get_latest_onchain_valuation",
        lambda live_btc_price=None: dict(VALID_ONCHAIN),
    )
    return client, ledger_calls


def _add_key(monkeypatch, key: str, role: UserRole) -> str:
    monkeypatch.setitem(security_config.API_KEYS_ENV, key, role)
    monkeypatch.setitem(security_auth.API_KEYS_ENV, key, role)
    return key


def _experiment_payload():
    return {
        "trials_count": 5,
        "macro_shock": "NEUTRAL",
        "commit_to_ledger": True,
    }


# ---------------------------------------------------------------------------
# 1. Arena experiment authorization
# ---------------------------------------------------------------------------
def test_anonymous_arena_experiment_cannot_commit_to_ledger(arena_client):
    client, ledger_calls = arena_client
    response = client.post("/api/arena/experiment", json=_experiment_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["parameters"]["commit_requested"] is True
    assert body["parameters"]["committed_to_ledger"] is False
    assert ledger_calls == []


def test_user_role_arena_experiment_cannot_commit_to_ledger(arena_client, monkeypatch):
    client, ledger_calls = arena_client
    key = _add_key(monkeypatch, "pytest-arena-user-key", UserRole.USER)
    response = client.post(
        "/api/arena/experiment", json=_experiment_payload(), headers={"X-API-Key": key}
    )
    assert response.status_code == 200
    assert response.json()["parameters"]["committed_to_ledger"] is False
    assert ledger_calls == []


def test_research_role_arena_experiment_cannot_commit_to_ledger(arena_client, monkeypatch):
    client, ledger_calls = arena_client
    key = _add_key(monkeypatch, "pytest-arena-research-key", UserRole.RESEARCH)
    response = client.post(
        "/api/arena/experiment", json=_experiment_payload(), headers={"X-API-Key": key}
    )
    assert response.status_code == 200
    assert response.json()["parameters"]["committed_to_ledger"] is False
    assert ledger_calls == []


def test_admin_arena_experiment_can_commit_to_ledger(arena_client, monkeypatch):
    client, ledger_calls = arena_client
    key = _add_key(monkeypatch, "pytest-arena-admin-key", UserRole.ADMIN)
    response = client.post(
        "/api/arena/experiment", json=_experiment_payload(), headers={"X-API-Key": key}
    )
    assert response.status_code == 200
    assert response.json()["parameters"]["committed_to_ledger"] is True
    assert len(ledger_calls) == 5
    assert all(call["data_source"] == "synthetic_arena" for call in ledger_calls)


def test_arena_experiment_rejects_invalid_token(arena_client):
    client, ledger_calls = arena_client
    response = client.post(
        "/api/arena/experiment",
        json=_experiment_payload(),
        headers={"X-API-Key": "not-a-configured-key"},
    )
    assert response.status_code == 401
    assert ledger_calls == []


# ---------------------------------------------------------------------------
# 2. Streaming body cap
# ---------------------------------------------------------------------------
def _asgi_post(chunks, headers, path="/echo"):
    async def receive():
        try:
            return next(chunk_iter)
        except StopIteration:
            return {"type": "http.disconnect"}

    async def run():
        sent = []

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": headers,
            "client": ("1.2.3.4", 4321),
            "server": ("testserver", 80),
            "state": {},
        }
        await limited_app(scope, receive, send)
        return sent

    chunk_iter = iter(chunks)
    return asyncio.run(run())


async def _echo_handler(request):
    body = await request.body()
    return JSONResponse({"len": len(body)})


limited_app = RateLimitingMiddleware(Starlette(routes=[Route("/echo", _echo_handler, methods=["POST"])]))
CHUNKED_HEADERS = [
    (b"host", b"testserver"),
    (b"transfer-encoding", b"chunked"),
    (b"content-type", b"application/json"),
]


@pytest.fixture(autouse=True)
def _silence_security_audit(monkeypatch):
    """Avoid writing payload-size / auth events into the on-disk audit log."""
    monkeypatch.setattr("engine.security_audit.security_audit.alert_critical", lambda *a, **k: None)


def test_chunked_body_over_cap_is_rejected_with_413():
    chunks = [
        {"type": "http.request", "body": b"x" * (MAX_REQUEST_BODY_BYTES // 2 + 1), "more_body": True},
        {"type": "http.request", "body": b"x" * (MAX_REQUEST_BODY_BYTES // 2 + 1), "more_body": True},
        {"type": "http.request", "body": b"", "more_body": False},
    ]
    sent = _asgi_post(chunks, CHUNKED_HEADERS)
    start = next(m for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    assert start["status"] == 413
    assert json.loads(body)["error"] == "PAYLOAD_TOO_LARGE"


def test_chunked_body_under_cap_is_passed_through():
    chunks = [
        {"type": "http.request", "body": b'{"trials_count": 5,', "more_body": True},
        {"type": "http.request", "body": b' "macro_shock": "NEUTRAL"}', "more_body": False},
    ]
    sent = _asgi_post(chunks, CHUNKED_HEADERS)
    start = next(m for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    assert start["status"] == 200
    assert json.loads(body)["len"] == len(b'{"trials_count": 5, "macro_shock": "NEUTRAL"}')


def test_normal_json_request_with_content_length_is_unaffected():
    client = TestClient(app, base_url="http://testserver", raise_server_exceptions=False)
    response = client.post("/api/arena/experiment", json=_experiment_payload())
    assert response.status_code == 200


def test_declared_content_length_over_cap_is_rejected_with_413():
    client = TestClient(app, base_url="http://testserver", raise_server_exceptions=False)
    oversized = {"blob": "x" * (MAX_REQUEST_BODY_BYTES + 1024)}
    response = client.post("/api/arena/experiment", json=oversized)
    assert response.status_code == 413
    assert response.json()["error"] == "PAYLOAD_TOO_LARGE"


# ---------------------------------------------------------------------------
# 3. Exception sanitisation
# ---------------------------------------------------------------------------
def test_sanitize_client_error_redacts_paths_and_database_uris():
    raw = "failed reading /home/ubuntu/bt/experiments/results/ledger.csv via sqlite:///home/ubuntu/bt/data/x.db"
    cleaned = sanitize_client_error(RuntimeError(raw))
    assert "/home/ubuntu" not in cleaned
    assert "sqlite:///" not in cleaned
    assert "[REDACTED_PATH]" in cleaned
    assert "[REDACTED_URI]" in cleaned


def test_sanitize_client_error_truncates_and_handles_empty_messages():
    assert len(sanitize_client_error(ValueError("y" * 5000))) <= 520
    assert sanitize_client_error(ValueError()) == "ValueError"


@pytest.mark.parametrize(
    "relative_path",
    ["api/routes_arena.py", "api/routes_market.py", "api/routes_prediction.py"],
)
def test_no_raw_exception_text_in_client_facing_payloads(relative_path):
    source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    leaks = re.findall(r"\"(?:error|reason|rejection_narrative|detail)\":\s*(?:str\(|\{[a-z]+\})", source)
    assert leaks == [], f"raw exception text still returned by {relative_path}: {leaks}"


def test_market_route_uses_sanitized_reason_on_failure(monkeypatch):
    import api.routes_market as routes_market

    def _boom(*args, **kwargs):
        raise RuntimeError("cannot open /home/ubuntu/bt/data/secret.csv")

    monkeypatch.setattr("engine.coinbase_15m_adapter.coinbase_15m_adapter.get_or_sync_15m_candles", _boom)
    client = TestClient(app, base_url="http://testserver", raise_server_exceptions=False)
    response = client.get("/candles", params={"interval": "15m"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "DATA_UNAVAILABLE"
    assert "/home/ubuntu" not in payload["reason"]
    assert routes_market is not None


# ---------------------------------------------------------------------------
# 4. Deployment configuration (Fly / Render) and health check
# ---------------------------------------------------------------------------
def _fly_config():
    with open(REPO_ROOT / "fly.toml", "rb") as handle:
        return tomllib.load(handle)


def test_fly_declares_trusted_host_and_cors_origin():
    env = _fly_config()["env"]
    hosts = [h.strip() for h in env["BTCOGNITIVE_ALLOWED_HOSTS"].split(",")]
    origins = [o.strip() for o in env["BTCOGNITIVE_ALLOWED_ORIGINS"].split(",")]
    assert "btcognitive-engine.fly.dev" in hosts
    assert "https://btcognitive-engine.fly.dev" in origins
    assert "https://btcognitive-engine.onrender.com" in origins


def test_render_declares_trusted_host_and_cors_origin():
    text = (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "BTCOGNITIVE_ALLOWED_HOSTS" in text
    assert "BTCOGNITIVE_ALLOWED_ORIGINS" in text
    assert "btcognitive-engine.onrender.com" in text


def test_fly_health_path_answers_for_fly_hostname():
    from api.market_monitor_routes import router as monitor_router

    env = _fly_config()["env"]
    hosts = [h.strip() for h in env["BTCOGNITIVE_ALLOWED_HOSTS"].split(",")]
    origins = [o.strip() for o in env["BTCOGNITIVE_ALLOWED_ORIGINS"].split(",")]

    deployed = FastAPI()
    deployed.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    deployed.add_middleware(
        CORSMiddleware, allow_origins=origins, allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"],
    )
    deployed.include_router(monitor_router)

    health_path = _fly_config()["checks"]["health"]["path"]
    ok_client = TestClient(deployed, base_url="http://btcognitive-engine.fly.dev")
    assert ok_client.get(health_path).status_code == 200

    rejected_client = TestClient(deployed, base_url="http://attacker.example")
    assert rejected_client.get(health_path).status_code == 400

    preflight = ok_client.options(
        "/api/health",
        headers={
            "Origin": "https://btcognitive-engine.fly.dev",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.headers.get("access-control-allow-origin") == "https://btcognitive-engine.fly.dev"


# ---------------------------------------------------------------------------
# 5. Token fingerprint logging
# ---------------------------------------------------------------------------
def test_auth_failure_logs_non_reversible_fingerprint(monkeypatch):
    captured = {}

    def _capture(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(security_auth.security_audit, "log_event", _capture)

    token = "super-secret-presented-token-1234567890"
    request = type(
        "FakeRequest",
        (),
        {
            "client": type("Client", (), {"host": "1.2.3.4"})(),
            "url": type("URL", (), {"path": "/api/arena/experiment"})(),
        },
    )()

    with pytest.raises(Exception) as excinfo:
        security_auth.get_current_user_role(request, api_key=token, bearer=None)
    assert getattr(excinfo.value, "status_code", None) == 401

    details = captured["details"]
    assert "provided_token_prefix" not in details
    assert details["provided_token_fingerprint"] == hashlib.sha256(token.encode()).hexdigest()[:12]
    assert details["provided_token_length"] == len(token)
    serialized = json.dumps(details)
    assert token[:6] not in serialized
    assert token not in serialized


# ---------------------------------------------------------------------------
# 7. Dockerfile runtime
# ---------------------------------------------------------------------------
def test_dockerfile_uses_python_313_for_both_stages():
    lines = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    from_lines = [line.strip() for line in lines if line.strip().upper().startswith("FROM ")]
    assert len(from_lines) == 2
    assert all(line.lower().startswith("from python:3.13-slim") for line in from_lines), from_lines
    assert not any("3.11" in line for line in from_lines)


# ---------------------------------------------------------------------------
# 6. Research-alert evaluation authorization (require_role(RESEARCH))
# ---------------------------------------------------------------------------
def test_anonymous_research_alert_evaluation_requires_research_role(monkeypatch):
    import api.routes_notifications as routes_notifications

    async def _fake_evaluate(force=False, ws_manager=None):
        return {"status": "FAKE"}

    monkeypatch.setattr(routes_notifications.notification_manager, "evaluate_research_conditions", _fake_evaluate)
    client = TestClient(app, base_url="http://testserver", raise_server_exceptions=False)
    response = client.post("/api/notifications/research-alerts/evaluate")
    assert response.status_code == 403
