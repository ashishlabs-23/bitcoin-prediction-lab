"""
tests/test_baseline_reconstruction.py — Unit Tests for Point-in-Time Baseline Comparison
========================================================================================
Verifies:
1. Baseline reconstruction for Ridge, Historical Percentile, ATR, and EWMA
2. Evaluation metrics: MAE, RMSE, MedAE, P90 Abs Error, Coverage
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.baseline_reconstruction import run_baseline_reconstruction


def test_baseline_reconstruction_execution():
    df_comp, _, meta = run_baseline_reconstruction()

    assert len(df_comp) == 4
    assert meta["n_eval"] == 276
    assert "MAE %" in df_comp.columns
    assert "MedAE %" in df_comp.columns
    assert "MFE P90 Coverage %" in df_comp.columns
