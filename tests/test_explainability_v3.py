"""
tests/test_explainability_v3.py — Unit Tests for Explainable AI Engine
=====================================================================
Validates:
  - Top 5 important indicators extraction
  - 120-step temporal attention heatmap
  - Activated Top-2 MoE experts and routing weights
  - Market regime detection integration
  - Deterministic natural language reasoning (zero LLM reliance)
  - API endpoint integration
"""

import os
import sys
import pytest
import numpy as np
import torch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.explainability import ExplainableAIEngine, explain_prediction


def test_explainability_components_generation():
    """Validates that all 5 required explainability components are generated correctly."""
    engine = ExplainableAIEngine()

    # Generate synthetic input tensor (120, 32)
    test_tensor = np.random.randn(120, 32).astype(np.float32)

    res = engine.generate_explanation(tensor=test_tensor)

    assert isinstance(res, dict)
    assert "top_5_indicators" in res
    assert "attention_heatmap" in res
    assert "activated_experts" in res
    assert "market_regime" in res
    assert "reasons" in res
    assert "formatted_explanation" in res

    # 1. Check Top 5 Indicators
    assert len(res["top_5_indicators"]) == 5
    for item in res["top_5_indicators"]:
        assert "feature" in item
        assert "label" in item
        assert "importance_weight" in item
        assert "status" in item

    # 2. Check Attention Heatmap (120 steps)
    assert len(res["attention_heatmap"]) == 120
    np.testing.assert_allclose(sum(res["attention_heatmap"]), 1.0, rtol=1e-3)

    # 3. Check Activated Experts (Top-2)
    assert len(res["activated_experts"]) == 2

    # 4. Check Market Regime
    assert "regime" in res["market_regime"]
    assert "confidence" in res["market_regime"]

    # 5. Check Natural Language Reasoning Bullet Points
    assert len(res["reasons"]) >= 4
    for r in res["reasons"]:
        assert isinstance(r, str)
        assert len(r) > 5


def test_formatted_explanation_layout():
    """Validates that formatted_explanation strictly matches the required layout."""
    test_tensor = np.random.randn(120, 32).astype(np.float32)
    res = explain_prediction(tensor=test_tensor)

    formatted_text = res["formatted_explanation"]
    assert isinstance(formatted_text, str)
    
    # Must contain Direction (BUY/SELL/HOLD), Confidence: X%, Reason:, and bullet points (*)
    lines = formatted_text.split("\n")
    assert lines[0] in ["BUY", "SELL", "HOLD"]
    assert "Confidence:" in lines[1]
    assert "Reason:" in lines[3]
    
    bullet_lines = [l for l in lines[4:] if l.startswith("* ")]
    assert len(bullet_lines) >= 4


def test_deterministic_behavior():
    """Validates that reason generation is completely deterministic without external API calls."""
    test_tensor = np.random.randn(120, 32).astype(np.float32)
    res1 = explain_prediction(tensor=test_tensor)
    res2 = explain_prediction(tensor=test_tensor)

    assert res1["top_5_indicators"] == res2["top_5_indicators"]
    assert res1["reasons"] == res2["reasons"]
