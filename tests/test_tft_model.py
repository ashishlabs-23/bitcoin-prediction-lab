"""
tests/test_tft_model.py — Unit Tests for Temporal Fusion Transformer
====================================================================
Validates:
  - TFT model architecture components and forward pass
  - Multi-task output heads (Cross Entropy classification + Quantile returns)
  - predict(tensor) structured JSON response format
  - Walk-forward training and checkpoint creation
"""

import os
import sys
import tempfile
import pytest
import numpy as np
import torch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.tft_model import TemporalFusionTransformer, predict
from training.train_tft import train_walk_forward, build_synthetic_training_data, QuantileLoss


def test_tft_architecture_forward():
    """Validates full TFT forward pass and sub-component output shapes."""
    model = TemporalFusionTransformer(num_features=32, seq_len=120, d_model=64)
    model.eval()

    # Batch shape (4, 120, 32)
    batch_input = torch.randn(4, 120, 32)
    with torch.no_grad():
        out = model(batch_input)

    assert "logits" in out
    assert "probabilities" in out
    assert "quantiles" in out
    assert "expected_volatility" in out
    assert "feature_weights" in out
    assert "attention_weights" in out

    # Check shapes
    assert out["logits"].shape == (4, 3)
    assert out["probabilities"].shape == (4, 3)
    assert out["quantiles"].shape == (4, 3)
    assert out["expected_volatility"].shape == (4,)
    assert out["feature_weights"].shape == (4, 120, 32)

    # Probabilities sum to 1.0
    prob_sums = out["probabilities"].sum(dim=-1)
    np.testing.assert_allclose(prob_sums.numpy(), np.ones(4), rtol=1e-5)


def test_single_tensor_input():
    """Validates single unbatched (120, 32) tensor input."""
    model = TemporalFusionTransformer(num_features=32, seq_len=120, d_model=64)
    model.eval()

    single_input = torch.randn(120, 32)
    with torch.no_grad():
        out = model(single_input)

    assert out["probabilities"].shape == (1, 3)
    assert out["quantiles"].shape == (1, 3)


def test_predict_structured_json():
    """Validates predict(tensor) structured JSON response."""
    test_tensor = np.random.randn(120, 32).astype(np.float32)
    pred_res = predict(test_tensor)

    assert isinstance(pred_res, dict)
    assert "direction" in pred_res
    assert pred_res["direction"] in ["BUY", "SELL", "HOLD"]
    assert "probabilities" in pred_res
    assert set(pred_res["probabilities"].keys()) == {"BUY", "SELL", "HOLD"}
    assert "expected_return_pct" in pred_res
    assert "expected_volatility" in pred_res
    assert "quantiles" in pred_res
    assert "confidence" in pred_res
    assert 0.0 <= pred_res["confidence"] <= 1.0


def test_walk_forward_training(tmp_path):
    """Validates walk-forward training execution and checkpoint creation."""
    checkpoint_file = str(tmp_path / "tft_test.pt")
    X, y_ret, y_dir, y_vol = build_synthetic_training_data(n_samples=80)

    train_res = train_walk_forward(
        X, y_ret, y_dir, y_vol,
        epochs=1,
        batch_size=16,
        checkpoint_out=checkpoint_file
    )

    assert train_res["status"] == "success"
    assert os.path.exists(checkpoint_file)
    assert os.path.getsize(checkpoint_file) > 1000 # Valid PyTorch weights file


def test_quantile_loss():
    """Validates pinball QuantileLoss computation."""
    q_loss = QuantileLoss(quantiles=[0.1, 0.5, 0.9])
    preds = torch.tensor([[0.01, 0.02, 0.03], [0.00, 0.01, 0.02]])
    targets = torch.tensor([0.02, 0.01])
    loss = q_loss(preds, targets)
    assert loss.item() >= 0.0
