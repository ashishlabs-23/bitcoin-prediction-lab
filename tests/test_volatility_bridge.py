"""
tests/test_volatility_bridge.py — Unit Tests for Volatility Bridge & Term Structure
===================================================================================
Verifies:
1. Computation of multi-timescale volatility ratios
2. Assignment of deterministic volatility transition regimes
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.volatility_bridge import volatility_bridge_service, VolatilityTermStructure


def test_volatility_term_structure_analysis():
    ts = volatility_bridge_service.analyze_term_structure(
        vol_5m=0.0018,
        vol_1h=0.0072,
        vol_4h=0.0125,
        vol_24h=0.0150
    )

    assert isinstance(ts, VolatilityTermStructure)
    assert ts.ratio_5m_24h > 0.0
    assert ts.ratio_1h_24h > 0.0
    assert ts.regime in ["VOL_EXPANDING", "VOL_COMPRESSION", "NORMAL", "PEAK_VOLATILITY"]
