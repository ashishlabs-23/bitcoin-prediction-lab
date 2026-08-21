"""
tests/test_microstructure_features.py — Unit Tests for 16 Canonical Microstructure Features
============================================================================================
Verifies:
1. Computation of all 16 microstructure factors
2. Finite non-null values and proper feature names
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.microstructure_dataset import generate_synthetic_l2_event_stream
from research.microstructure_features import extract_microstructure_features, MICROSTRUCTURE_FEATURE_NAMES


def test_microstructure_feature_extraction():
    df_raw = generate_synthetic_l2_event_stream(n_events=150)
    feats = extract_microstructure_features(df_raw)

    assert len(feats) == 150
    assert len(feats.columns) == 16
    for col in MICROSTRUCTURE_FEATURE_NAMES:
        assert col in feats.columns
        assert not feats[col].isnull().any()
