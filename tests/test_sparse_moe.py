"""
tests/test_sparse_moe.py — Unit Tests for Sparse Mixture of Experts (MoE)
=========================================================================
Validates:
  - 5 individual specialized experts (Trend, Breakout, Scalping, Volatility, News)
  - Router sparse Top-2 gating (only 2 experts active, non-selected = 0 weight)
  - Top-2 weights sum to 1.0
  - Combined directional probabilities (BUY, SELL, HOLD)
  - predict_moe() structured JSON response
  - Router checkpoint persistence to models/checkpoints/router.pt
"""

import os
import sys
import pytest
import numpy as np
import torch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.experts.trend import TrendExpert
from models.experts.breakout import BreakoutExpert
from models.experts.scalping import ScalpingExpert
from models.experts.volatility import VolatilityExpert
from models.experts.news import NewsExpert
from models.router import SparseMoE, predict_moe, save_router_checkpoint, EXPERT_NAMES


def test_individual_experts_forward():
    """Validates that each of the 5 specialized experts executes and produces valid outputs."""
    experts = [
        TrendExpert(num_features=32),
        BreakoutExpert(num_features=32),
        ScalpingExpert(num_features=32),
        VolatilityExpert(num_features=32),
        NewsExpert(num_features=32)
    ]

    test_input = torch.randn(2, 120, 32)
    for expert in experts:
        expert.eval()
        with torch.no_grad():
            out = expert(test_input)

        assert "probabilities" in out
        assert "confidence" in out
        assert "expected_return" in out
        assert out["probabilities"].shape == (2, 3)
        prob_sums = out["probabilities"].sum(dim=-1).numpy()
        np.testing.assert_allclose(prob_sums, np.ones(2), rtol=1e-5)


def test_sparse_top2_gating_behavior():
    """Validates that Router selects strictly Top-2 experts with exactly 2 non-zero weights summing to 1.0."""
    moe = SparseMoE(num_features=32, regime_dim=7, k=2)
    moe.eval()

    test_tensor = torch.randn(4, 120, 32)
    test_regime = torch.zeros(4, 7)
    test_regime[:, 0] = 1.0 # Strong Uptrend

    with torch.no_grad():
        out = moe(test_tensor, test_regime)

    sparse_weights = out["sparse_weights"] # (4, 5)
    topk_indices = out["topk_indices"]     # (4, 2)
    topk_weights = out["topk_weights"]     # (4, 2)

    assert sparse_weights.shape == (4, 5)
    assert topk_indices.shape == (4, 2)
    assert topk_weights.shape == (4, 2)

    # Verify that exactly 2 entries are non-zero per sample
    non_zero_counts = (sparse_weights > 0).sum(dim=-1).numpy()
    np.testing.assert_array_equal(non_zero_counts, np.array([2, 2, 2, 2]))

    # Verify that Top-2 weights sum to 1.0
    weight_sums = sparse_weights.sum(dim=-1).numpy()
    np.testing.assert_allclose(weight_sums, np.ones(4), rtol=1e-5)


def test_predict_moe_output_format():
    """Validates predict_moe structured JSON format."""
    test_tensor = np.random.randn(120, 32).astype(np.float32)
    regime_data = {"regime": "Strong Uptrend", "confidence": 0.95}

    res = predict_moe(test_tensor, regime_data=regime_data)

    assert isinstance(res, dict)
    assert "direction" in res
    assert res["direction"] in ["BUY", "SELL", "HOLD"]
    assert "probabilities" in res
    assert set(res["probabilities"].keys()) == {"BUY", "SELL", "HOLD"}
    assert "confidence" in res
    assert 0.0 <= res["confidence"] <= 1.0
    assert "selected_experts" in res
    assert len(res["selected_experts"]) == 2 # Top-2
    assert "all_expert_weights" in res
    assert len(res["all_expert_weights"]) == 5


def test_router_checkpoint_persistence(tmp_path):
    """Validates saving and loading router checkpoint."""
    checkpoint_file = str(tmp_path / "router_test.pt")
    moe = SparseMoE(num_features=32, regime_dim=7, k=2)

    saved_path = save_router_checkpoint(moe, path=checkpoint_file)
    assert os.path.exists(saved_path)
    assert os.path.getsize(saved_path) > 1000

    # Load and test
    test_tensor = np.random.randn(120, 32).astype(np.float32)
    res = predict_moe(test_tensor, checkpoint_path=checkpoint_file)
    assert res["direction"] in ["BUY", "SELL", "HOLD"]
