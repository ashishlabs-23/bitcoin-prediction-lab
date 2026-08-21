"""
tests/test_foundation_quantiles.py — Unit Tests for Foundation Quantile Normalization
=====================================================================================
Verifies:
1. Normalization of sample paths into canonical P10/P50/P90 quantiles
2. Monotonicity of excursion bounds (P90 >= P50 >= P10)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.foundation.uncertainty_adapter import FoundationUncertaintyAdapter


def test_foundation_quantile_normalization():
    paths = [65200.0 * (1.0 + (i - 10) * 0.001) for i in range(21)]
    norm = FoundationUncertaintyAdapter.normalize_quantiles(paths, current_price=65200.0)

    assert norm["mfe_p90"] >= norm["mfe_p50"] >= norm["mfe_p10"]
    assert norm["mae_p90"] >= norm["mae_p50"] >= norm["mae_p10"]
    assert norm["upper_p90"] > norm["lower_p90"]
    assert 0.8 <= norm["uncertainty"] <= 5.0
