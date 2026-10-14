"""
tests/test_agent_d_frontend_regression.py — Agent D Frontend, Packaging & Data Integrity Suite
=============================================================================================
Covers:
1. No synthetic fallbacks: missing market data must remain unavailable / fail closed.
   Verifies that missing spot price never invents 65000, 60000, 64250, or 64000.
2. Local packaging integrity: .dockerignore allows web/ and web_dist/ for frontend serving.
3. Frontend module build smoke test: executes node build_frontend.js.
"""

import os
import sys
import subprocess
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app
from engine.evidence_router import AdaptiveEvidenceRouter


def test_missing_market_data_fails_closed_without_synthetic_fallbacks(monkeypatch):
    """
    Verify that when spot price / market data is missing, live inference endpoints
    fail closed or return explicit unavailable state rather than fabricating fake prices.
    """
    # Clear feature cache price
    from engine.feature_cache import feature_cache
    monkeypatch.setattr(feature_cache, "get_latest_price", lambda: 0.0)
    monkeypatch.setattr(feature_cache, "get_latest_row", lambda: None)

    from engine.observatory import observatory
    monkeypatch.setattr(observatory, "get_canonical_snapshot", lambda: None)

    client = TestClient(app)

    # 1. MEIE state endpoint must return 503 instead of 60,000.0
    res_meie = client.get("/api/arena/meie/state")
    assert res_meie.status_code == 503
    assert "Market price unavailable" in res_meie.json()["detail"]

    # 2. Multiscale prediction endpoint must return 503 instead of 65,000.0
    res_multi = client.get("/prediction/multiscale")
    assert res_multi.status_code == 503
    assert "Market price unavailable" in res_multi.json()["detail"]

    # 3. Active paper position must report MARKET_DATA_UNAVAILABLE instead of 64,250.0
    res_pos = client.get("/api/arena/active-paper-position")
    assert res_pos.status_code == 200
    pos_data = res_pos.json()
    assert pos_data.get("status") == "MARKET_DATA_UNAVAILABLE"
    assert pos_data.get("live_price") is None

    # 4. Adaptive evidence router must fail closed with SPOT_PRICE_UNAVAILABLE instead of 64,000.0
    router = AdaptiveEvidenceRouter()
    res_route = router.decompose_decision_questions(horizon="15m", market_snapshot={})
    assert res_route.get("solver_fail_closed") is True
    assert res_route.get("fail_closed_reason") == "SPOT_PRICE_UNAVAILABLE"


def test_dockerignore_allows_web_frontend():
    """Verify .dockerignore does not exclude web/ or web_dist/ needed to serve the dashboard."""
    dockerignore_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".dockerignore"))
    assert os.path.exists(dockerignore_path)

    with open(dockerignore_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines()]

    # Assert web/ and web_dist/ are not excluded
    assert "web/" not in lines, ".dockerignore erroneously excludes web/"
    assert "web_dist/" not in lines, ".dockerignore erroneously excludes web_dist/"


def test_frontend_build_and_module_smoke():
    """Execute node build_frontend.js and ensure all modules pass syntax and smoke checks."""
    proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    result = subprocess.run(
        ["node", "build_frontend.js"],
        cwd=proj_root,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Frontend build script failed:\n{result.stderr}\n{result.stdout}"
    assert "Frontend Build and Verification Complete: SUCCESS" in result.stdout
