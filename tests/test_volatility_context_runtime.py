"""
tests/test_volatility_context_runtime.py — Unit Tests for Production Runtime Path
================================================================================
Verifies:
1. End-to-end execution of the combined Ridge + Volatility Context pipeline
2. Inclusion of context fields in GET /prediction/range
"""

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
    assert data["model_version"] == "v3.0.0-excursion-ridge-conformal"
    assert data["context_version"] == "v1.0.0-volatility-bridge-context"
    assert data["context_status"] == "CONTEXT_HEALTHY"
    assert "volatility_state" in data
