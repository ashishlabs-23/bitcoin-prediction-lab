"""
tests/test_observed_vs_projected.py — Unit Tests for Observed vs Target Metric Integrity
========================================================================================
Verifies:
1. 'results/longitudinal_metrics.csv' contains ONLY real observed blocks
2. 'results/longitudinal_targets.csv' contains target definitions with zero fake precision
"""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.production_longitudinal_report import generate_longitudinal_evidence_and_targets
from research.longitudinal_integrity_audit import run_longitudinal_integrity_audit


def test_observed_vs_target_separation():
    dfo, dft, mf = generate_longitudinal_evidence_and_targets()

    assert len(dfo) == 1
    assert dfo["Independent Blocks"].iloc[0] == 31
    assert dfo["Evidence Tier"].iloc[0] == "CURRENT_OBSERVED_EVIDENCE"

    assert len(dft) == 6
    assert dft["Observation Status"].str.contains("TARGET").all()


def test_longitudinal_integrity_audit_verdict():
    df_a, meta = run_longitudinal_integrity_audit()

    assert len(df_a) == 7
    assert meta["verdict"] == "LONGITUDINAL_MONITORING_INTEGRITY_VERIFIED"
    assert meta["observed_blocks"] == 31
    assert meta["target_blocks"] == 90
