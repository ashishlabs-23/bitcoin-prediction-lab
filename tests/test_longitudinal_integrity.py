"""
tests/test_longitudinal_integrity.py — Unit Tests for Longitudinal Data Integrity Guards
========================================================================================
Verifies:
1. Rejection of reused historical data predating the frozen validation boundary
2. Rejection of model hash mismatches
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.longitudinal_monitor import longitudinal_evidence_store


def test_longitudinal_reused_data_rejection():
    stale_record = {
        "forecast_id": "REUSED-001",
        "forecast_timestamp": "2026-08-10T12:00:00Z",  # Before frozen boundary
        "outcome_timestamp": "2026-08-11T12:00:00Z",
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
        "block_id": 10
    }
    assert longitudinal_evidence_store.record_evidence(stale_record) is False


def test_longitudinal_model_hash_mismatch_rejection():
    mutated_record = {
        "forecast_id": "MUTATED-001",
        "forecast_timestamp": "2026-08-22T12:00:00Z",
        "outcome_timestamp": "2026-08-23T12:00:00Z",
        "model_version": "unauthorized-model-v4",
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
        "block_id": 33
    }
    assert longitudinal_evidence_store.record_evidence(mutated_record) is False
