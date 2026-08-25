"""
tests/test_hawkes_replay.py — Unit Tests for Hawkes Deterministic Prediction Replay
===================================================================================
Verifies:
1. Exact deterministic reproduction of historical Hawkes predictions
2. Detection of numerical divergence (HAWKES_REPRODUCTION_FAILURE)
"""

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.hawkes_replay import run_deterministic_replay_test, replay_hawkes_prediction, HawkesReplayError
from models.challengers.microstructure_range import ShortHorizonRangeModel


def test_hawkes_deterministic_replay_success():
    res = run_deterministic_replay_test()
    assert res["status"] == "REPRODUCIBLE"
    assert res["is_reproducible"] is True


def test_hawkes_replay_detects_mutation():
    model = ShortHorizonRangeModel()
    feat_vec = np.ones(23, dtype=np.float32) * 0.5
    pred = model.predict_microstructure(feat_vec, horizon="5m")

    # Mutate expected output to induce divergence
    pred.mfe_p50 += 0.05

    with pytest.raises(HawkesReplayError):
        replay_hawkes_prediction(feat_vec, pred, tolerance=1e-5)
