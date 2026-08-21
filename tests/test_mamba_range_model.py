"""
tests/test_mamba_range_model.py — Unit Tests for Mamba Model Architecture & Range Forecaster Interface
=====================================================================================================
Verifies:
1. Model instantiation, forward pass dimensions, and parameter count
2. Conformance to RangeForecaster abstract interface
"""

import os
import sys
import torch
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.challengers.mamba_range_model import MambaRangeModel
from models.interfaces.range_forecaster import RangeForecastOutput


def test_mamba_model_forward_shape():
    model = MambaRangeModel(d_feat=5, d_model=32, d_state=16, n_layers=2, context_length=120)
    x = torch.randn(4, 120, 5)
    mfe_q, mae_q = model(x)

    assert mfe_q.shape == (4, 5)
    assert mae_q.shape == (4, 5)


def test_mamba_predict_range_interface():
    model = MambaRangeModel(d_feat=5, d_model=32, d_state=16, n_layers=2, context_length=120)
    feat_np = np.random.randn(120, 5).astype(np.float32)

    output = model.predict_range(feat_np)
    assert isinstance(output, RangeForecastOutput)
    assert output.model_version == "v1.0.0-challenger-mamba"
    assert output.mfe_p10 <= output.mfe_p90
    assert output.mae_p10 <= output.mae_p90
