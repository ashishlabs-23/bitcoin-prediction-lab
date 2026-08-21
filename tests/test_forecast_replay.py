"""
tests/test_forecast_replay.py — Unit Tests for Deterministic Forecast Replay
=============================================================================
Verifies:
1. Exact reproducible forecast reconstruction
2. ForecastReproductionFailure raised on intentional mismatch
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.forecast_replay import replay_forecast, ForecastReproductionFailure
from research.forecast_audit import run_forecast_audit


def test_deterministic_forecast_replay_success():
    feat = {"vol_24h": 0.015, "rsi_14": 52.0}
    fc = replay_forecast("2026-08-21T00:00:00Z", "v3.0.0-excursion-ridge-conformal", 65000.0, 0.015, feat)

    assert fc.mfe_p50 > 0.0
    assert fc.upper_p90 > 65000.0


def test_forecast_replay_failure_on_corrupted_snapshot():
    feat = {"vol_24h": 0.015, "rsi_14": 52.0}
    corrupted_snapshot = {"mfe_p50": 0.9999, "mae_p50": 0.001, "upper_p90": 999999.0}

    with pytest.raises(ForecastReproductionFailure):
        replay_forecast("2026-08-21T00:00:00Z", "v3.0.0-excursion-ridge-conformal", 65000.0, 0.015, feat, stored_snapshot=corrupted_snapshot)


def test_forecast_audit_sampling():
    rep = run_forecast_audit(sample_size=10)
    assert rep["failures"] == 0
    assert rep["audit_verdict"] == "PERFECT_REPRODUCIBILITY"
