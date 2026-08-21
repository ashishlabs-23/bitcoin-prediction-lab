"""
tests/test_regime_detector_v3.py — Unit Tests for Market Regime Detector
========================================================================
Validates:
  - 7 standard regimes identification
  - Feature extraction from dict, dataframe, and numpy tensor
  - Exact output format: {"regime": "...", "confidence": float}
  - Two-stage training (unsupervised clustering + supervised refinement)
  - Checkpoint saving and persistence to models/checkpoints/regime.pt
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd
import torch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.regime_detector import (
    MarketRegimeDetector,
    detect_regime,
    REGIMES,
    NUM_REGIMES,
    REGIME_CHECKPOINT_PATH
)


def test_regimes_list_and_count():
    """Validates that all 7 required regimes are defined."""
    assert NUM_REGIMES == 7
    expected = [
        "Strong Uptrend",
        "Weak Uptrend",
        "Sideways",
        "Accumulation",
        "Distribution",
        "High Volatility",
        "Capitulation"
    ]
    assert REGIMES == expected


def test_detect_regime_output_format():
    """Validates that detect_regime returns the exact required JSON schema."""
    input_data = {
        "ATR": 0.025,
        "ADX": 0.35,
        "EMA Slopes": 0.015,
        "Volume": 1.8,
        "VWAP": 0.008,
        "Funding Rate": 0.0003
    }
    res = detect_regime(input_data)

    assert isinstance(res, dict)
    assert "regime" in res
    assert "confidence" in res
    assert res["regime"] in REGIMES
    assert isinstance(res["confidence"], float)
    assert 0.0 <= res["confidence"] <= 1.0


def test_feature_extraction_varieties():
    """Validates feature extraction from dict, DataFrame, and numpy array."""
    detector = MarketRegimeDetector()

    # 1. From dict
    d_feat = detector.extract_features({"ATR": 0.02, "ADX": 0.4, "Volume": 1.2})
    assert d_feat.shape == (1, 7)

    # 2. From DataFrame
    df = pd.DataFrame({
        "atr_14_ratio": [0.01, 0.02, 0.03],
        "adx_14": [0.2, 0.3, 0.4],
        "ema_20_ratio": [0.005, 0.01, 0.015],
        "ema_50_ratio": [0.002, 0.005, 0.008],
        "norm_volume": [0.5, 1.0, 1.5],
        "vwap_ratio": [0.001, 0.002, 0.003],
        "funding_rate": [0.0001, 0.0001, 0.0001]
    })
    df_feat = detector.extract_features(df)
    assert df_feat.shape == (3, 7)

    # 3. From 32-dim tensor
    tensor_32 = np.random.randn(5, 32).astype(np.float32)
    t_feat = detector.extract_features(tensor_32)
    assert t_feat.shape == (5, 7)


def test_training_and_checkpoint_saving(tmp_path):
    """Validates two-stage unsupervised + supervised training and checkpoint persistence."""
    checkpoint_file = str(tmp_path / "regime_test.pt")
    detector = MarketRegimeDetector(checkpoint_path=checkpoint_file)

    # Generate synthetic training data across regimes
    np.random.seed(42)
    synthetic_data = np.random.randn(100, 7).astype(np.float32)

    fit_res = detector.fit(synthetic_data, epochs=3)
    assert fit_res["status"] == "trained"
    assert os.path.exists(checkpoint_file)
    assert os.path.getsize(checkpoint_file) > 500

    # Test re-loading from checkpoint
    loaded_detector = MarketRegimeDetector(checkpoint_path=checkpoint_file)
    sample_res = loaded_detector.predict({"ATR": 0.03, "Volume": 2.5})
    assert sample_res["regime"] in REGIMES
    assert 0.0 <= sample_res["confidence"] <= 1.0
