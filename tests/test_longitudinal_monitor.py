"""
tests/test_longitudinal_monitor.py — Unit Tests for Longitudinal Evidence Store
================================================================================
Verifies:
1. Append-only persistence in SQLite
2. Hard safety invariant: LONGITUDINAL_MONITORING_ONLY = True
"""

import os
import sqlite3
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import research.longitudinal_monitor as longitudinal_monitor
from research.longitudinal_monitor import (
    LongitudinalEvidenceStore,
    LONGITUDINAL_MONITORING_ONLY,
    PRODUCTION_MODEL_VERSION
)


def test_longitudinal_monitor_safety_invariants():
    assert LONGITUDINAL_MONITORING_ONLY is True
    assert PRODUCTION_MODEL_VERSION == "v3.0.0-excursion-ridge-conformal"


def test_default_store_proxy_preserves_method_access(monkeypatch):
    class FakeStore:
        def count_records(self):
            return 7

    monkeypatch.setattr(longitudinal_monitor, "LongitudinalEvidenceStore", FakeStore)
    proxy = longitudinal_monitor._LazyLongitudinalEvidenceStore()

    assert proxy.count_records() == 7


def test_longitudinal_evidence_store_operations(tmp_path):
    store = LongitudinalEvidenceStore(str(tmp_path / "longitudinal_monitor.db"))
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
    res = store.record_evidence(rec)
    assert res is True
    assert store.count_records() == 1

    retry = dict(rec)
    retry.update(
        outcome_timestamp="2026-08-24T04:00:00Z",
        actual_high=70000.0,
        actual_low=60000.0,
        actual_close=69000.0,
        actual_mfe=0.08,
        actual_mae=0.07,
        winkler_score=9999.0,
        data_quality="MUTATED",
    )
    assert store.record_evidence(retry) is False
    assert store.count_records() == 1

    with sqlite3.connect(store.db_path) as conn:
        row = conn.execute(
            """
            SELECT outcome_timestamp, actual_high, actual_low, actual_close,
                   actual_mfe, actual_mae, winkler_score, data_quality
            FROM longitudinal_forecasts
            WHERE forecast_id = ?
            """,
            (rec["forecast_id"],),
        ).fetchone()
    assert row == (
        rec["outcome_timestamp"],
        rec["actual_high"],
        rec["actual_low"],
        rec["actual_close"],
        rec["actual_mfe"],
        rec["actual_mae"],
        rec["winkler_score"],
        rec["data_quality"],
    )
