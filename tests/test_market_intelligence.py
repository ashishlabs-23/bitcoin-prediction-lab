"""
Unit tests for Market Intelligence Engine in models/market_intelligence.py.
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.market_intelligence import MarketIntelligenceEngine
from models.train_baselines import make_dataset


def test_market_intelligence_all_engines():
    """Verify that MarketIntelligenceEngine returns complete 6-engine JSON structure."""
    X, y, t1 = make_dataset(horizon_bars=24)
    engine = MarketIntelligenceEngine()

    intel = engine.compute_all(X)

    assert "structure" in intel
    assert "liquidity" in intel
    assert "momentum" in intel
    assert "volatility" in intel
    assert "confidence" in intel
    assert "narrative" in intel
    assert "timestamp" in intel

    # Structure assertions
    struct = intel["structure"]
    assert "label" in struct
    assert "sequence_desc" in struct
    assert "trend_strength_pct" in struct

    # Liquidity assertions
    liq = intel["liquidity"]
    assert "risk_level" in liq
    assert "sweep_target_price" in liq

    # Momentum assertions
    mom = intel["momentum"]
    assert "status" in mom
    assert "strength_pct" in mom
    assert "acceleration" in mom

    # Volatility assertions
    vol = intel["volatility"]
    assert "volatility_state" in vol
    assert "historical_percentile_pct" in vol
    assert "breakout_probability" in vol

    # Narrative assertion
    assert isinstance(intel["narrative"], str)
    assert len(intel["narrative"]) > 20
