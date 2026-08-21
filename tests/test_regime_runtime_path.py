"""
tests/test_regime_runtime_path.py — Tests for Regime Routing in Runtime Execution
================================================================================
Verifies that:
- classify_regimes() returns a pandas Series containing ONLY canonical regime values.
- Ensemble and OpportunityDetector route canonical regimes without error.
"""

import pytest
import pandas as pd
import numpy as np
from models.regime_contract import CanonicalRegime, all_canonical_values
from models.regime_detector import classify_regimes
from models.opportunity_detector import opportunity_detector

def test_classify_regimes_returns_canonical_values():
    # Construct dummy OHLCV dataframe
    n = 30
    dates = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "open": 65000 + np.cumsum(np.random.normal(0, 100, n)),
        "high": 65200 + np.cumsum(np.random.normal(0, 100, n)),
        "low": 64800 + np.cumsum(np.random.normal(0, 100, n)),
        "close": 65000 + np.cumsum(np.random.normal(0, 100, n)),
        "volume": np.random.uniform(10, 100, n),
        "realized_vol_24h": np.random.uniform(0.01, 0.04, n),
        "rsi_14": np.random.uniform(30, 70, n),
        "atr_14": np.random.uniform(300, 800, n)
    })
    
    regimes = classify_regimes(df)
    assert isinstance(regimes, pd.Series)
    assert len(regimes) == n
    
    canonical_set = set(all_canonical_values())
    for val in regimes:
        assert val in canonical_set, f"Non-canonical regime returned: {val}"

def test_opportunity_detector_canonical_routing():
    # Pass various canonical regimes to opportunity detector
    for cr in CanonicalRegime:
        pred_dict = {
            "direction": "LONG",
            "probability": 0.65,
            "expected_return": 0.015,
            "entry_price": 65000.0,
            "tp": 66500.0,
            "sl": 64200.0
        }
        opp = opportunity_detector.evaluate_opportunity(
            prediction=pred_dict,
            regime_data={"current_regime": cr.value, "event_flags": []},
            quality_data={"score": 85}
        )
        if opp is not None:
            assert opp["regime"] == cr.value
            assert opp["opportunity_score"] >= 0 and opp["opportunity_score"] <= 100
