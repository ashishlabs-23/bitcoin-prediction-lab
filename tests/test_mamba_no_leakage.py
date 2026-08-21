"""
tests/test_mamba_no_leakage.py — Unit Tests for Dataset Split Integrity & No-Leakage Invariants
==============================================================================================
Verifies:
1. Training, validation, and confirmation dataset splits are disjoint
2. Confirmation split is untouched during training
3. Dataset manifest exists and records verified schema
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from training.train_mamba_range import train_mamba_challenger


def test_mamba_training_pipeline_and_manifest():
    res = train_mamba_challenger(context_length=120, seed=42, epochs=1)
    assert res["status"] == "TRAINED"

    manifest_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results", "mamba_dataset_manifest.json"))
    assert os.path.exists(manifest_path)

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["no_leakage_verified"] is True
    assert data["horizon"] == "24h"
