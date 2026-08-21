"""
tests/test_production_lock.py — Unit Tests for Production Lock Immutability & Hash Integrity
============================================================================================
Verifies:
1. Existence and valid schema of results/production_lock.json
2. Checksums match real physical files and feature schemas
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.production_hash_audit import run_production_hash_audit


def test_production_lock_manifest_integrity():
    lock_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results", "production_lock.json"))
    assert os.path.exists(lock_path), "production_lock.json missing!"

    with open(lock_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["model_version"] == "v3.0.0-excursion-ridge-conformal"
    assert data["production_safety_invariants"]["auto_retraining_allowed"] is False
    assert data["production_safety_invariants"]["real_trading_allowed"] is False


def test_production_hash_audit_execution():
    rep, verified = run_production_hash_audit()
    assert verified is True
    assert rep["audit_status"] == "PROVENANCE_VALID"
