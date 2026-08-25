"""
tests/test_quantitative_suite_v3.py — Unit Tests for Quantitative Validation Suite
==================================================================================
Validates:
  - Computation of all 7 quantitative metrics (Accuracy, Precision, Recall, ROC AUC, Profit Factor, Sharpe, DSR)
  - Multi-model evaluation across TFT, 5 Experts, Router, and Meta Labeler
  - Strict DSR-only model ranking
  - Automated leaderboard export to CSV, Parquet, and Markdown
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.evaluator import compute_metrics, evaluate_models
from research.leaderboard import ModelLeaderboard, generate_and_export_leaderboard


def test_metrics_calculation_completeness():
    """Validates that compute_metrics returns all 7 expected keys with valid ranges."""
    y_true = np.array([0, 1, 0, 2, 1, 0, 1, 2, 0, 1])
    y_pred = np.array([0, 1, 0, 1, 1, 0, 2, 2, 0, 1])
    y_prob = np.random.dirichlet((1, 1, 1), size=10)
    rets = np.array([0.01, 0.02, 0.005, -0.01, 0.015, 0.008, -0.02, 0.002, 0.012, 0.018])

    m = compute_metrics(y_true, y_pred, y_prob, rets)

    expected_keys = ["accuracy", "precision", "recall", "roc_auc", "profit_factor", "sharpe", "dsr"]
    for k in expected_keys:
        assert k in m
        assert isinstance(m[k], float)

    assert 0.0 <= m["accuracy"] <= 1.0
    assert 0.0 <= m["precision"] <= 1.0
    assert 0.0 <= m["recall"] <= 1.0
    assert 0.0 <= m["roc_auc"] <= 1.0
    assert m["profit_factor"] >= 0.0


def test_evaluate_all_v3_models():
    """Validates that evaluate_models evaluates TFT, 5 Experts, Router, and Meta Labeler."""
    np.random.seed(42)
    n = 20
    tensors = np.random.randn(n, 120, 32).astype(np.float32)
    y_true = np.random.choice([0, 1, 2], size=n, p=[0.45, 0.45, 0.10])
    returns = np.random.normal(loc=0.004, scale=0.015, size=n).astype(np.float32)

    res = evaluate_models(tensors, y_true, returns)
    assert isinstance(res, list)
    assert len(res) == 8 # TFT + 5 Experts + Router + Meta Labeler

    model_names = [r["model"] for r in res]
    assert any("TFT" in name for name in model_names)
    assert "TrendExpert" in model_names
    assert "BreakoutExpert" in model_names
    assert "ScalpingExpert" in model_names
    assert "VolatilityExpert" in model_names
    assert "NewsExpert" in model_names
    assert "Sparse MoE Router" in model_names
    assert any("Meta Labeler" in name for name in model_names)


def test_leaderboard_dsr_ranking_and_exports(tmp_path):
    """Validates that models are strictly ranked by DSR and exported to CSV, Parquet, and Markdown."""
    board = ModelLeaderboard(results_dir=str(tmp_path))

    np.random.seed(42)
    n = 30
    tensors = np.random.randn(n, 120, 32).astype(np.float32)
    y_true = np.random.choice([0, 1, 2], size=n, p=[0.45, 0.45, 0.10])
    returns = np.random.normal(loc=0.005, scale=0.012, size=n).astype(np.float32)

    df = board.generate_leaderboard(tensors=tensors, y_true=y_true, returns=returns)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 8

    # Verify DSR descending order
    dsr_vals = df["DSR"].values
    for i in range(len(dsr_vals) - 1):
        assert dsr_vals[i] >= dsr_vals[i + 1]

    # Verify Exports
    c_file = str(tmp_path / "leaderboard.csv")
    p_file = str(tmp_path / "leaderboard.parquet")
    m_file = str(tmp_path / "leaderboard.md")

    exports = board.export_all(df, csv_path=c_file, parquet_path=p_file, md_path=m_file)
    assert os.path.exists(exports["csv"])
    assert os.path.exists(exports["parquet"])
    assert os.path.exists(exports["markdown"])

    # Verify Markdown file contains table headers
    with open(exports["markdown"], "r", encoding="utf-8") as f:
        md_text = f.read()
    assert "| Rank | Model | DSR | Sharpe |" in md_text
    assert "# BTCognitive V3 — Quantitative Model Leaderboard" in md_text
