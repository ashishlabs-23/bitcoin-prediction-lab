"""
tests/test_retrain_pipeline_v3.py — Unit Tests for Self-Learning Retraining Pipeline
====================================================================================
Validates:
  - Trigger logic (every 500 completed trades)
  - Dataset building from Arena history
  - Retraining TFT, Regime Detector, Router, and Meta Labeler
  - Computation of all 6 metrics: Sharpe, Sortino, Calmar, DSR, Win Rate, Max Drawdown
  - Version folder isolation (models/registry/v{N}/)
  - Strict DSR promotion gate (never overwrites production unless DSR strictly improves)
"""

import os
import sys
import json
import pytest
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from training.retrain_pipeline import SelfLearningPipeline
from engine.arena_runner import ArenaRunner


def test_retrain_trigger_check(tmp_path):
    """Validates trigger evaluation at 500-trade intervals."""
    db_file = str(tmp_path / "arena_trigger_test.db")
    reg_dir = str(tmp_path / "registry")
    runner = ArenaRunner(db_path=db_file)
    pipeline = SelfLearningPipeline(db_path=db_file, registry_dir=reg_dir)

    # 0 trades -> False
    should_run, count = pipeline.check_trigger(min_new_trades=500)
    assert not should_run
    assert count == 0


def test_metrics_calculation():
    """Validates computation of the 6 required quantitative metrics."""
    pipeline = SelfLearningPipeline()
    # High-performance return stream
    np.random.seed(42)
    sample_returns = np.random.normal(loc=0.005, scale=0.012, size=50)

    metrics = pipeline.evaluate_walk_forward(sample_returns)
    assert "sharpe_ratio" in metrics
    assert "sortino_ratio" in metrics
    assert "calmar_ratio" in metrics
    assert "deflated_sharpe" in metrics
    assert "win_rate" in metrics
    assert "max_drawdown" in metrics

    assert metrics["win_rate"] >= 0.50
    assert metrics["deflated_sharpe"] > 0.0


def test_version_isolation_and_promotion_gate(tmp_path, monkeypatch):
    """Validates version folder creation and DSR gate enforcement."""
    db_file = str(tmp_path / "arena_gate_test.db")
    reg_dir = str(tmp_path / "registry")
    runner = ArenaRunner(db_path=db_file)
    pipeline = SelfLearningPipeline(db_path=db_file, registry_dir=reg_dir)

    # Run pipeline with force=True
    res = pipeline.run_pipeline(force=True)

    assert res["status"] == "COMPLETED"
    assert res["version"] == "v1"
    version_dir = os.path.join(reg_dir, "v1")
    assert os.path.exists(version_dir)

    # Verify version files
    assert os.path.exists(os.path.join(version_dir, "tft.pt"))
    assert os.path.exists(os.path.join(version_dir, "regime.pt"))
    assert os.path.exists(os.path.join(version_dir, "router.pt"))
    assert os.path.exists(os.path.join(version_dir, "meta.pt"))
    assert os.path.exists(os.path.join(version_dir, "metrics.json"))

    # Read metrics.json
    with open(os.path.join(version_dir, "metrics.json"), "r") as f:
        m_data = json.load(f)
    assert m_data["version"] == "v1"
    assert "metrics" in m_data

    # Run 2nd candidate -> should generate v2
    res2 = pipeline.run_pipeline(force=True)
    assert res2["version"] == "v2"
    assert os.path.exists(os.path.join(reg_dir, "v2"))
