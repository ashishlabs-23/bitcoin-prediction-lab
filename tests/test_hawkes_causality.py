"""
tests/test_hawkes_causality.py — Unit Tests for Hawkes Model Causality & Intensities
====================================================================================
Verifies:
1. Hawkes intensity extraction
2. Strictly causal evaluation (perturbing event at t=100 does not affect t<=50)
"""

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.microstructure_dataset import generate_synthetic_l2_event_stream
from models.challengers.hawkes_microstructure import hawkes_model


def test_hawkes_intensity_output_schema():
    df_raw = generate_synthetic_l2_event_stream(n_events=100)
    intensities = hawkes_model.compute_intensities(df_raw)

    assert len(intensities) == 100
    assert "lambda_buy" in intensities.columns
    assert "lambda_sell" in intensities.columns
    assert "event_cluster_score" in intensities.columns
    assert (intensities["lambda_buy"] > 0).all()


def test_hawkes_causality_invariance():
    df_base = generate_synthetic_l2_event_stream(n_events=80)
    df_pert = df_base.copy()

    # Perturb the last event
    df_pert.loc[79, "signed_volume"] = 100.0
    df_pert.loc[79, "event_type"] = "trade"

    h_base = hawkes_model.compute_intensities(df_base)
    h_pert = hawkes_model.compute_intensities(df_pert)

    # First 50 steps must be strictly identical
    diff = np.abs(h_base.iloc[:50].values - h_pert.iloc[:50].values).max()
    assert diff < 1e-6, f"Future event leaked backward in Hawkes model! diff={diff}"
