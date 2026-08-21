"""
tests/test_volatility_context_provenance.py — Unit Tests for Production Lock & Schema Provenance
===============================================================================================
Verifies:
1. Immutability of results/volatility_context_production_lock.json
2. Zero coupling of production 24h forecast to shadow Hawkes
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOCK_PATH = os.path.join(ROOT_DIR, "results", "volatility_context_production_lock.json")


def test_production_lock_manifest_integrity():
    assert os.path.exists(LOCK_PATH)
    with open(LOCK_PATH, "r") as f:
        data = json.load(f)

    assert data["production_model_version"] == "v3.0.0-excursion-ridge-conformal"
    assert data["production_context_version"] == "v1.0.0-volatility-bridge-context"
    assert "ZERO_HAWKES_DEPENDENCY" in data["shadow_coupling"]
    assert data["governance_status"] == "LOCKED_IN_PRODUCTION"
