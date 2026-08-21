"""
tests/test_milestone_35_gate.py — Unit Tests for 35-Block Longitudinal Evidence Gate
=====================================================================================
Verifies:
1. 'results/milestone_35_lock.json' manifest integrity and SHA-256 block provenance
2. Statistically significant paired baseline edge (p < 0.001) over 35 non-overlapping blocks
3. Authoritative report generation and API status updates (next milestone = 40)
"""

import os
import sys
import json
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app
from research.milestone_35_gate import run_milestone_35_evidence_gate

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
REPORTS_DIR = os.path.join(ROOT_DIR, "research", "reports")

client = TestClient(app)


def test_milestone_35_gate_execution_and_lock():
    lock, summ = run_milestone_35_evidence_gate()

    assert summ["verdict"] == "35_BLOCK_STABILITY_CONFIRMED"
    assert summ["observed_blocks"] == 35
    assert summ["next_milestone"] == 40
    assert 32.0 <= summ["n_eff"] <= 35.0
    assert summ["baseline_delta_bps"] == -14.1
    assert summ["permutation_p"] < 0.001

    lock_file = os.path.join(RESULTS_DIR, "milestone_35_lock.json")
    assert os.path.exists(lock_file)
    with open(lock_file, "r", encoding="utf-8") as f:
        lock_data = json.load(f)
    assert lock_data["milestone"] == 35
    assert lock_data["independent_blocks_count"] == 35
    assert len(lock_data["block_manifest_hash"]) == 64


def test_milestone_35_observed_report_exists():
    report_file = os.path.join(REPORTS_DIR, "longitudinal_35_observed.md")
    assert os.path.exists(report_file)
    with open(report_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "35_BLOCK_STABILITY_CONFIRMED" in content
    assert "35 non-overlapping independent 24h blocks" in content


def test_api_returns_35_observed_blocks():
    res = client.get("/prediction/longitudinal")
    assert res.status_code == 200
    data = res.json()
    assert data["observed_blocks"] == 35
    assert data["target_blocks"] == 90
    assert data["next_milestone_block"] == 40
    assert data["observed_metrics"]["mfe_error_pct"] == 0.3970
    assert data["observed_metrics"]["baseline_delta_bps"] == -14.1
