"""
tests/test_meta_labeler.py — Unit Tests for Meta Labeler Institutional Trade Filter
===================================================================================
Validates:
  - Meta feature extraction and Shannon entropy computation
  - Expert agreement scoring
  - Tri-state decisions: Execute (1.0x), Reject (0.0x), Reduce Size (0.5x)
  - Sharpe-surrogate loss optimization
  - Checkpoint saving to models/checkpoints/meta.pt and re-loading
  - evaluate_trade_filter() execution pipeline
"""

import os
import sys
import pytest
import numpy as np
import torch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.meta_labeler import (
    MetaLabeler,
    evaluate_trade_filter,
    compute_shannon_entropy,
    compute_expert_agreement,
    SharpeSurrogateLoss,
    DECISION_CLASSES,
    SIZING_MAP,
    META_CHECKPOINT_PATH
)


def test_shannon_entropy_bounds():
    """Validates Shannon entropy is in range [0.0, 1.0]."""
    # Deterministic signal (low entropy -> 0.0)
    ent_low = compute_shannon_entropy([0.99, 0.005, 0.005])
    assert 0.0 <= ent_low < 0.2

    # Maximum uncertainty uniform distribution (high entropy -> 1.0)
    ent_high = compute_shannon_entropy([0.3333, 0.3333, 0.3334])
    assert ent_high > 0.95


def test_expert_agreement():
    """Validates cosine similarity agreement across expert predictions."""
    e1 = {"probabilities": {"BUY": 0.80, "SELL": 0.10, "HOLD": 0.10}}
    e2 = {"probabilities": {"BUY": 0.85, "SELL": 0.08, "HOLD": 0.07}}
    agree_high = compute_expert_agreement([e1, e2])
    assert agree_high > 0.95

    # Conflicting experts
    e3 = {"probabilities": {"BUY": 0.05, "SELL": 0.90, "HOLD": 0.05}}
    agree_low = compute_expert_agreement([e1, e3])
    assert agree_low < 0.5


def test_meta_labeler_decision_outputs():
    """Validates that predict() returns valid tri-state decisions and sizing multipliers."""
    labeler = MetaLabeler()
    res = labeler.predict(
        tft_probs={"BUY": 0.75, "SELL": 0.10, "HOLD": 0.15},
        expert_agreement=0.92,
        atr=0.012,
        spread=0.0001,
        funding=0.0001,
        rsi=55.0,
        volatility=0.015
    )

    assert isinstance(res, dict)
    assert res["decision"] in DECISION_CLASSES
    assert res["sizing_multiplier"] in [1.0, 0.0, 0.5]
    assert 0.0 <= res["confidence"] <= 1.0
    assert "decision_probabilities" in res
    assert set(res["decision_probabilities"].keys()) == set(DECISION_CLASSES)


def test_evaluate_trade_filter_api():
    """Validates high-level evaluate_trade_filter() entrypoint."""
    tft_probs = [0.82, 0.08, 0.10]
    expert_outs = [
        {"probabilities": {"BUY": 0.80, "SELL": 0.10, "HOLD": 0.10}},
        {"probabilities": {"BUY": 0.85, "SELL": 0.05, "HOLD": 0.10}}
    ]
    market_metrics = {
        "atr": 0.014,
        "spread": 0.0002,
        "funding": 0.0001,
        "rsi": 58.0,
        "volatility": 0.018
    }

    out = evaluate_trade_filter(tft_probs, expert_outputs=expert_outs, market_metrics=market_metrics)
    assert out["decision"] in ["Execute", "Reject", "Reduce Size"]
    assert out["sizing_multiplier"] == SIZING_MAP[out["decision"]]


def test_sharpe_surrogate_loss_and_training(tmp_path):
    """Validates Sharpe ratio optimization loss and checkpoint persistence."""
    checkpoint_file = str(tmp_path / "meta_test.pt")
    labeler = MetaLabeler(checkpoint_path=checkpoint_file)

    # Synthetic meta-features & forward trade returns
    np.random.seed(42)
    n_samples = 60
    meta_feats = np.random.randn(n_samples, 10).astype(np.float32)
    # Target trade returns: mix of positive and negative returns
    rets = np.random.normal(loc=0.003, scale=0.015, size=n_samples).astype(np.float32)

    fit_res = labeler.fit(meta_feats, rets, epochs=3)
    assert fit_res["status"] == "trained"
    assert os.path.exists(checkpoint_file)
    assert os.path.getsize(checkpoint_file) > 500

    # Load and test
    loaded = MetaLabeler(checkpoint_path=checkpoint_file)
    pred = loaded.predict(tft_probs=[0.7, 0.1, 0.2])
    assert pred["decision"] in DECISION_CLASSES
