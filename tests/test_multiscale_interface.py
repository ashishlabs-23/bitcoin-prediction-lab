"""
tests/test_multiscale_interface.py — Unit Tests for Multiscale Forecaster Interface
====================================================================================
Verifies:
1. Multiscale interface conformance
2. Dual-horizon range forecast generation
"""

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.multiscale_research import ResearchMultiscaleForecaster, MultiscaleForecastResult


def test_multiscale_forecaster_dual_horizon():
    forecaster = ResearchMultiscaleForecaster()
    dummy_micro = np.random.randn(23).astype(np.float32)
    dummy_macro = {"close": 65000.0, "vol_24h": 0.015}

    res = forecaster.predict_multiscale(dummy_micro, dummy_macro)
    assert isinstance(res, MultiscaleForecastResult)
    assert res.short_term_horizon == "15m"
    assert res.long_term_horizon == "24h"
    assert res.status == "RESEARCH_SYNCHRONIZED"
