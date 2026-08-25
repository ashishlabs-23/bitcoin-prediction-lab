"""
tests/test_microstructure_range.py — Unit Tests for Short-Horizon Range Model & Quantiles
=========================================================================================
Verifies:
1. Microstructure range model forward pass
2. Strict monotonic quantile ordering P10 <= P50 <= P90
"""

import os
import sys
import torch
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.challengers.microstructure_range import ShortHorizonRangeModel, MicrostructureRangePrediction


def test_short_horizon_range_model_quantiles():
    model = ShortHorizonRangeModel(d_in=23)
    feat_vec = np.random.randn(23).astype(np.float32)

    pred = model.predict_microstructure(feat_vec, horizon="5m")
    assert isinstance(pred, MicrostructureRangePrediction)
    assert pred.horizon == "5m"
    assert pred.mfe_p10 <= pred.mfe_p50 <= pred.mfe_p90
    assert pred.mae_p10 <= pred.mae_p50 <= pred.mae_p90
    assert 0.0 <= pred.prob_up <= 1.0
    assert 0.0 <= pred.prob_down <= 1.0
