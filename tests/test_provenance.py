"""
tests/test_provenance.py — Unit Tests for Cryptographic Provenance Verification
================================================================================
Verifies:
1. Production lock manifest checksum integrity
2. SHA-256 computation and field presence
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.provenance_audit import run_provenance_audit, compute_sha256, ProvenanceError


def test_provenance_audit_passes():
    res = run_provenance_audit()
    assert res["status"] == "VERIFIED"
    assert "sha256:" in res["model_checksum"]
    assert "sha256:" in res["feature_schema_hash"]


def test_sha256_computation_deterministic():
    h1 = compute_sha256("test_payload")
    h2 = compute_sha256("test_payload")
    assert h1 == h2
    assert h1.startswith("sha256:")
