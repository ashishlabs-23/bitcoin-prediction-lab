"""Production forecasts remain blocked while safe empirical baselines are non-authorizing."""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.volatility_context_runtime_audit import audit_production_runtime_path
from api.server import app

client = TestClient(app)


def test_production_runtime_path_audit():
    df_a, meta = audit_production_runtime_path()

    assert len(df_a) == 5
    assert meta["is_runtime_integrated"] is True
    assert meta["shadow_coupling"] == "ZERO"


def test_get_prediction_range_context_fields():
    response = client.get("/prediction/range")
    assert response.status_code == 200

    data = response.json()
    assert data["forecast_mode"] == "EXPERIMENTAL_BASELINE"
    assert data["research_authorization"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert data["validation_status"] == "NOT_VALIDATED_FOR_TRADING"
    assert data["live_capital_authorized"] is False
    assert data["direction"] == "NOT_ESTIMATED"
    assert data["probability"] is None
    assert "model_version" not in data
    assert "context_version" not in data
    assert data["availability"] in {"AVAILABLE", "UNAVAILABLE"}
