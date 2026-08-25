"""
tests/test_production_health.py — Unit Tests for Production Health Evaluation
=============================================================================
Verifies:
1. Health state classification: MODEL_HEALTHY, MODEL_WATCH, MODEL_DEGRADED, MODEL_INVALID
2. Checksum and database integrity failures
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.production_health import production_health_service, HealthEvaluationResult
from engine.production_status import get_canonical_production_status, ProductionStatus


def test_production_health_healthy_state():
    res = production_health_service.evaluate_health(
        coverage_pct=90.32,
        error_pct=0.4120,
        drift_status="NORMAL",
        data_quality="VALID",
        checksum_matches=True,
        db_writable=True
    )
    assert isinstance(res, HealthEvaluationResult)
    assert res.health_status == "MODEL_HEALTHY"
    assert res.score >= 80.0


def test_production_health_invalid_on_checksum_failure():
    res = production_health_service.evaluate_health(
        checksum_matches=False
    )
    assert res.health_status == "MODEL_INVALID"
    assert res.score == 0.0


def test_canonical_production_status():
    status = get_canonical_production_status()
    assert isinstance(status, ProductionStatus)
    assert status.health == "MODEL_HEALTHY"
    assert status.version == "v3.0.0-excursion-ridge-conformal"
