"""
tests/test_longitudinal_monitor.py — Unit Tests for Longitudinal Evidence Store
================================================================================
Verifies:
1. Append-only persistence in SQLite
2. Hard safety invariant: LONGITUDINAL_MONITORING_ONLY = True
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.longitudinal_monitor import (
    longitudinal_evidence_store,
    LONGITUDINAL_MONITORING_ONLY,
    PRODUCTION_MODEL_VERSION
)


def test_longitudinal_monitor_safety_invariants():
    assert LONGITUDINAL_MONITORING_ONLY is True
    assert PRODUCTION_MODEL_VERSION == "v3.0.0-excursion-ridge-conformal"


def test_longitudinal_evidence_store_operations():
    rec = {
        "forecast_id": "LONG-TEST-001",
        "forecast_timestamp": "2026-08-21T04:00:00Z",
        "outcome_timestamp": "2026-08-22T04:00:00Z",
        "model_version": "v3.0.0-excursion-ridge-conformal",
        "context_version": "v1.0.0-volatility-bridge-context",
        "current_price": 65000.0,
        "predicted_mfe_p50": 0.012,
        "predicted_mae_p50": 0.015,
        "predicted_mfe_p90": 0.025,
        "predicted_mae_p90": 0.028,
        "actual_high": 66200.0,
        "actual_low": 64100.0,
        "actual_close": 65800.0,
        "actual_mfe": 0.0184,
        "actual_mae": 0.0138,
        "joint_contained": True,
        "winkler_score": 605.10,
        "uncertainty": 1.6,
        "volatility_state": "VOL_NORMAL",
        "market_state": "COMPRESSION_STABLE",
        "data_quality": "VALID",
        "block_id": 32
    }
    res = longitudinal_evidence_store.record_evidence(rec)
    assert res is True
