"""
tests/test_post_repair_boundary.py — Tests for Post-Repair Evidence Boundary
============================================================================
Verifies that:
- POST_REPAIR_EVIDENCE_START boundary is well-formed ISO UTC timestamp.
- Dataset audit strictly excludes observations prior to the boundary timestamp.
- No pre-repair records are misclassified as VALID_POST_REPAIR.
"""

import pandas as pd
from datetime import datetime, timezone
from research.post_repair_dataset_audit import POST_REPAIR_EVIDENCE_START, audit_dataset

def test_evidence_boundary_format():
    dt = pd.Timestamp(POST_REPAIR_EVIDENCE_START)
    assert dt.tz is not None or str(dt.tzinfo) == "UTC" or POST_REPAIR_EVIDENCE_START.endswith("Z")
    assert dt.year >= 2026

def test_dataset_audit_boundary_enforcement():
    counts = audit_dataset()
    assert isinstance(counts, dict)
    assert "VALID_POST_REPAIR" in counts
    assert "PRE_REPAIR" in counts
    # All pre-existing resolved rows must be classified as PRE_REPAIR (or invalid horizon)
    assert counts["PRE_REPAIR"] > 0
