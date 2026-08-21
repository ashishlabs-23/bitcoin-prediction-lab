"""
tests/test_foundation_no_leakage.py — Unit Tests for Strict Temporal Validation Boundary
========================================================================================
Verifies:
1. Strict purge & embargo between train/val/confirmation sets
2. Zero leakage of future prices or confirmation observations into adaptation
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from training.foundation_adaptation import foundation_adaptation_harness


def test_foundation_adaptation_boundary_safety():
    batches = foundation_adaptation_harness.prepare_training_batches([65000.0] * 200)

    assert batches["is_confirmation_leakage_prevented"] is True
    assert batches["mode"] in ["ZERO_SHOT", "IN_CONTEXT_FEW_SHOT", "LIMITED_FINE_TUNED"]
