"""
tests/test_v29_1_deployment_integrity.py — V29.1 Deployment Integrity & Production Verification
================================================================================================
Validates:
1. Production mode: BTC_ENVIRONMENT=production disables /docs, /redoc, /openapi.json.
2. Storage persistence: SQLITE_DB_PATH, MEIE_DB_PATH, and volume mount contracts.
3. Docker Compose & Fly.io configuration syntax and mount invariants.
4. Forecast contract: Research-only labelling and live trading disabling.
"""

import os
import re
import pytest
from starlette.testclient import TestClient

def test_production_environment_docs_disabled(monkeypatch):
    """Verify that in production mode, interactive OpenAPI/Swagger docs are disabled."""
    monkeypatch.setenv("BTC_ENVIRONMENT", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")

    # Import server and instantiate test client
    from api.server import app
    client = TestClient(app, raise_server_exceptions=False)

    # In production, docs should return 404
    res_docs = client.get("/docs")
    res_redoc = client.get("/redoc")
    res_openapi = client.get("/openapi.json")

    assert res_docs.status_code == 404, f"Expected 404 for /docs in production, got {res_docs.status_code}"
    assert res_redoc.status_code == 404, f"Expected 404 for /redoc in production, got {res_redoc.status_code}"
    assert res_openapi.status_code == 404, f"Expected 404 for /openapi.json in production, got {res_openapi.status_code}"


def test_sqlite_storage_paths_env_configurable(monkeypatch):
    """Verify that SQLite database paths respect environment overrides for container volume mounts."""
    test_db = "/tmp/test_market_memory.db"
    test_meie = "/tmp/test_meie.db"
    monkeypatch.setenv("SQLITE_DB_PATH", test_db)
    monkeypatch.setenv("MEIE_DB_PATH", test_meie)

    # Re-evaluate config
    import importlib
    import config.database
    importlib.reload(config.database)

    assert config.database.MARKET_MEMORY_DB_PATH == test_db

    import engine.arena_accounts
    importlib.reload(engine.arena_accounts)
    assert engine.arena_accounts.MEIE_DB_PATH == test_meie


def test_docker_compose_file_validity():
    """Verify docker-compose.yml configuration invariants."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    compose_path = os.path.join(repo_root, "docker-compose.yml")
    assert os.path.isfile(compose_path), "docker-compose.yml must exist"

    with open(compose_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must NOT have obsolete version tag
    assert "version:" not in content, "Obsolete top-level version key must be removed"

    # Must set BTC_ENVIRONMENT=production
    assert "BTC_ENVIRONMENT=production" in content or "BTC_ENVIRONMENT: production" in content

    # Must mount persistent data and experiments/results
    assert "./data:/app/data" in content or "./data: /app/data" in content
    assert "./experiments/results:/app/experiments/results" in content or "./experiments/results: /app/experiments/results" in content

    # Healthcheck must use /health
    assert "http://localhost:8000/health" in content


def test_fly_toml_configuration():
    """Verify fly.toml configuration invariants."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    fly_path = os.path.join(repo_root, "fly.toml")
    assert os.path.isfile(fly_path), "fly.toml must exist"

    with open(fly_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'BTC_ENVIRONMENT = "production"' in content
    assert "[mounts]" in content
    assert 'destination = "/app/data"' in content
    assert 'path         = "/health"' in content


def test_forecast_contract_disclaimers_and_governance():
    """Verify /api/forecast/latest enforces research-only contract and disabled trading."""
    from api.server import app
    client = TestClient(app, raise_server_exceptions=False)

    res = client.get("/api/forecast/latest?horizon=15m")
    assert res.status_code == 200
    data = res.json()

    assert data.get("status") == "FORECAST_AVAILABLE_RESEARCH_ONLY"
    assert data.get("forecast_readiness") == "FORECAST_AVAILABLE_RESEARCH_ONLY"
    assert data.get("directional_signal") == "ABSTAIN"
    assert data.get("directional_recommendation_status") == "DISABLED"
    assert data.get("live_trading") == "DISABLED"
    assert "disclaimer" in data
    assert "Research-only" in data["disclaimer"]
    assert len(data.get("points", [])) == 5
    assert len(data.get("upper_band", [])) == 5
    assert len(data.get("lower_band", [])) == 5
