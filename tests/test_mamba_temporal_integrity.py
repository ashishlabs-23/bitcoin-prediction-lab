"""
tests/test_mamba_temporal_integrity.py — Causal Temporal Behavior & No-Future-Leakage Tests
============================================================================================
Verifies:
1. Strict causal temporal processing (past -> present only)
2. Modifying future timestamps does not alter historical hidden representations
"""

import os
import sys
import torch
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.challengers.mamba_range_model import MambaRangeModel


def test_mamba_causal_temporal_invariance():
    model = MambaRangeModel(d_feat=5, d_model=32, d_state=16, n_layers=2, context_length=120)
    model.eval()

    # Create base sequence of length 100
    x_base = torch.randn(1, 100, 5)

    # Sequence with future modification at step 99
    x_perturbed = x_base.clone()
    x_perturbed[:, 99, :] += 50.0

    # Layer 1 causal check: hidden representation at step 50 must be identical
    with torch.no_grad():
        h_base = model.input_proj(x_base)
        h_base = model.layers[0](h_base)

        h_pert = model.input_proj(x_perturbed)
        h_pert = model.layers[0](h_pert)

    # Slices before perturbation (t <= 50) must match
    diff = torch.abs(h_base[:, :50, :] - h_pert[:, :50, :]).max().item()
    assert diff < 1e-5, f"Future information leaked backward into past steps! diff={diff}"
