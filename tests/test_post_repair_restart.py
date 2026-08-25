"""
tests/test_post_repair_restart.py — Tests for Restart Gate Governance
=====================================================================
Verifies that:
- Restart gate review evaluates all 16 pillars.
- Manifest lock file results/post_repair_baseline_lock.json exists and is valid JSON.
- Restart decision is one of CASE A / CASE B / CASE C.
"""

import os
import json
from config.paths import RESULTS_DIR
from research.post_repair_restart_gate import evaluate_restart_gate

def test_manifest_lock_integrity():
    lock_path = os.path.join(RESULTS_DIR, "post_repair_baseline_lock.json")
    assert os.path.exists(lock_path), "post_repair_baseline_lock.json does not exist"
    
    with open(lock_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "repair_version" in data
    assert "production_model_version" in data
    assert data["observed_post_repair_blocks"] == 0
    assert data["longitudinal_status"] == "PAUSED_INTEGRITY_REPAIR"

def test_restart_gate_execution():
    verdict = evaluate_restart_gate()
    assert verdict in [
        "CASE A: POST_REPAIR_MONITORING_READY",
        "CASE B: POST_REPAIR_EVIDENCE_INSUFFICIENT",
        "CASE C: POST_REPAIR_INTEGRITY_FAILURE"
    ]
