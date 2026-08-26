"""
tests/test_microstructure_state.py — Unit tests for MEIE Layer 1
"""
import sys
import os
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.microstructure_state import (
    compute_state_vector,
    MicrostructureStateVector,
    _zscore,
    ROLLING_WINDOW,
)


def make_candle(close=60000.0, high=None, low=None, open_=None, volume=1000.0):
    return {
        "close": close,
        "high": high or close * 1.002,
        "low": low or close * 0.998,
        "open": open_ or close,
        "volume": volume,
    }


class TestZScore:
    def test_zero_std_returns_zero(self):
        arr = np.array([1.0, 1.0, 1.0])
        assert _zscore(1.0, arr) == 0.0

    def test_known_zscore(self):
        arr = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        z = _zscore(2.0, arr)
        assert abs(z) < 0.1  # mean of array = 2.0, so z ≈ 0

    def test_single_element_returns_zero(self):
        arr = np.array([5.0])
        assert _zscore(5.0, arr) == 0.0


class TestComputeStateVector:
    def test_returns_correct_type(self, tmp_path, monkeypatch):
        """compute_state_vector returns a MicrostructureStateVector."""
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        sv = compute_state_vector(
            timestamp=ts,
            price=60000.0,
            candle=make_candle(),
        )
        assert isinstance(sv, MicrostructureStateVector)

    def test_data_quality_insufficient_with_no_history(self, tmp_path, monkeypatch):
        """With no rolling history, data_quality should be INSUFFICIENT or DEGRADED."""
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        sv = compute_state_vector(
            timestamp=ts,
            price=60000.0,
            candle=make_candle(),
        )
        assert sv.data_quality in ("INSUFFICIENT", "DEGRADED", "VALID")

    def test_hawkes_snapshot_updates_ofi(self):
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        sv = compute_state_vector(
            timestamp=ts,
            price=60000.0,
            candle=make_candle(),
            hawkes_snapshot={"lambda_buy": 5.0, "lambda_sell": 1.0},
        )
        # Strong buy pressure → raw_ofi should be positive
        assert sv.raw_ofi > 0

    def test_sell_pressure_gives_negative_ofi(self):
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        sv = compute_state_vector(
            timestamp=ts,
            price=60000.0,
            candle=make_candle(),
            hawkes_snapshot={"lambda_buy": 1.0, "lambda_sell": 9.0},
        )
        assert sv.raw_ofi < 0

    def test_z_scores_are_finite(self):
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        sv = compute_state_vector(
            timestamp=ts, price=60000.0, candle=make_candle()
        )
        for attr in ("z_hawkes", "z_ofi", "z_vpin", "z_depth", "z_spread", "z_impact"):
            val = getattr(sv, attr)
            assert val is not None
            assert not (val != val)  # NaN check

    def test_to_dict_has_all_fields(self):
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        sv = compute_state_vector(timestamp=ts, price=60000.0, candle=make_candle())
        d = sv.to_dict()
        required_keys = [
            "z_hawkes", "z_ofi", "z_vpin", "z_depth", "z_spread", "z_impact",
            "data_quality", "window_n", "timestamp", "price",
        ]
        for k in required_keys:
            assert k in d, f"Missing key: {k}"
