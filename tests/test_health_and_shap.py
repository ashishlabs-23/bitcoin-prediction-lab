"""
Unit tests for /health endpoint & real SHAP explanation calculation.
"""

import sys
import os
import pytest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.explainability import compute_shap_explanations
from models.ensemble import AdaptiveRegimeEnsemble
from models.train_baselines import make_dataset


def test_shap_explanation_calculation():
    """Verify real SHAP tree feature attribution computation returns factors and summary."""
    X, y, t1 = make_dataset(horizon_bars=24)
    ens = AdaptiveRegimeEnsemble()
    ens.fit(X.iloc[:100], y.iloc[:100])

    exp = compute_shap_explanations(ens, X.iloc[100:110])
    assert "summary" in exp
    assert "factors" in exp
    assert isinstance(exp["factors"], list)
    assert len(exp["factors"]) > 0
    assert "feature" in exp["factors"][0]
    assert "contribution" in exp["factors"][0]
