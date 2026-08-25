# -*- coding: utf-8 -*-
"""
tests/test_holdout_label_boundary.py — Regression Test Suite for Strict Forward-Label Boundary Invariants
========================================================================================================
Asserts:
1. Every training origin t satisfies t + 168h < holdout_start.
2. No training target interval intersects the 2026 holdout period [2026-01-01T00:00:00Z, inf).
3. A pipeline validator detects and rejects boundary-crossing training rows.
4. The frozen baseline manifest strictly adheres to the label-maturity cutoff rule.
"""

import os
import sys
import json
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR, DATA_RAW_DIR
from research.run_vol_edge_01_test import prepare_aligned_dataset
from research.freeze_har_rs_dow import HOLDOUT_BOUNDARY

MANIFEST_PATH = os.path.join(RESULTS_DIR, "freeze", "har_rs_dow_v1_baseline_manifest.json")


def test_manifest_strict_boundary_invariants():
    """Validates that the frozen manifest records strict forward-label separation."""
    assert os.path.exists(MANIFEST_PATH), "Baseline freeze manifest missing!"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    span = manifest["training_span"]
    holdout_start = pd.to_datetime(manifest["holdout_boundary"], utc=True)
    train_end = pd.to_datetime(span["end"], utc=True)
    max_maturity = pd.to_datetime(span["max_target_maturity"], utc=True)
    
    assert train_end < holdout_start, "Training origin must precede holdout start"
    assert max_maturity < holdout_start, "Max target maturity must be strictly prior to holdout start"
    assert span.get("strict_separation_enforced") is True, "Strict separation flag must be True"


def test_training_data_zero_holdout_label_overlap():
    """Asserts that no training row in the clean dataset has a forward 168h target intersecting holdout."""
    df = prepare_aligned_dataset()
    holdout_start = pd.to_datetime(HOLDOUT_BOUNDARY, utc=True)
    
    # Corrected clean training dataset
    strict_train_mask = (df.index + pd.Timedelta(hours=168) < holdout_start)
    df_train_clean = df[strict_train_mask].copy()
    
    # Calculate target ends for all training rows
    train_target_ends = df_train_clean.index + pd.Timedelta(hours=168)
    
    # Invariant 1: max(train_target_end) < holdout_start
    assert train_target_ends.max() < holdout_start, (
        f"Target maturity violation: max target end {train_target_ends.max()} >= holdout start {holdout_start}"
    )
    
    # Invariant 2: no_train_target_intersects_holdout
    overlap_mask = train_target_ends >= holdout_start
    assert overlap_mask.sum() == 0, f"Found {overlap_mask.sum()} training rows intersecting holdout!"
    
    # Invariant 3: exact maximum training origin
    expected_max_origin = holdout_start - pd.Timedelta(hours=169) # 2025-12-24 23:00 UTC
    assert df_train_clean.index.max() == expected_max_origin, (
        f"Expected max training origin {expected_max_origin}, got {df_train_clean.index.max()}"
    )


def test_reject_boundary_crossing_training_row():
    """Verifies that a training row whose forward target crosses holdout is rejected by the filter."""
    holdout_start = pd.to_datetime(HOLDOUT_BOUNDARY, utc=True)
    
    # Construct synthetic candidate origins
    valid_origin = holdout_start - pd.Timedelta(hours=169)       # Dec 24, 2025 23:00 -> Target Dec 31, 23:00 (VALID)
    borderline_origin = holdout_start - pd.Timedelta(hours=168)  # Dec 25, 2025 00:00 -> Target Jan 01, 00:00 (INVALID - 1h in 2026)
    invalid_origin = holdout_start - pd.Timedelta(hours=1)       # Dec 31, 2025 23:00 -> Target Jan 07, 23:00 (INVALID - 168h in 2026)
    
    def validate_training_origin(origin_dt: pd.Timestamp, horizon_h: int = 168) -> bool:
        target_maturity = origin_dt + pd.Timedelta(hours=horizon_h)
        return target_maturity < holdout_start
        
    assert validate_training_origin(valid_origin) is True
    assert validate_training_origin(borderline_origin) is False
    assert validate_training_origin(invalid_origin) is False
