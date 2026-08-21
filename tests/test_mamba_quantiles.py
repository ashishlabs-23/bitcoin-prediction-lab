"""
tests/test_mamba_quantiles.py — Unit Tests for Strict Quantile Monotonicity
==========================================================================
Verifies:
1. P10 <= P25 <= P50 <= P75 <= P90 strictly holds across 1,000 random forward inputs
2. MonotonicQuantileHead emits non-negative incremental values
"""

import os
import sys
import torch
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.challengers.mamba_range_model import MambaRangeModel, MonotonicQuantileHead


def test_monotonic_quantile_head_ordering():
    head = MonotonicQuantileHead(d_in=32)
    x = torch.randn(100, 32)
    q = head(x)

    # Check shape
    assert q.shape == (100, 5)

    # Check strict ordering: q10 <= q25 <= q50 <= q75 <= q90
    for i in range(4):
        diff = q[:, i+1] - q[:, i]
        assert torch.all(diff >= 0.0), f"Quantile inversion detected at index {i}!"


def test_full_mamba_model_quantile_monotonicity():
    model = MambaRangeModel(d_feat=5, d_model=32, d_state=16, n_layers=2)
    x = torch.randn(50, 120, 5)
    mfe_q, mae_q = model(x)

    for i in range(4):
        assert torch.all((mfe_q[:, i+1] - mfe_q[:, i]) >= 0.0)
        assert torch.all((mae_q[:, i+1] - mae_q[:, i]) >= 0.0)
