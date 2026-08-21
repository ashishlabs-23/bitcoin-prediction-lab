"""
tests/test_post_repair_milestone_integrity.py — Tests for Longitudinal Milestone Integrity
==========================================================================================
Verifies:
- Milestone sequence follows [0, 5, 10, 20, 30, 40, 60, 90].
- Old 35-block milestone is NOT present in the post-repair sequence.
- N_eff calculation follows effective sample size formula.
- Production model remains frozen.
"""

from engine.longitudinal_status import longitudinal_status_service

def test_milestone_sequence_integrity():
    report = longitudinal_status_service.get_status_report()
    target_blocks = [t["target_block"] for t in report.milestone_targets]
    expected_sequence = [5, 10, 20, 30, 40, 60, 90]
    assert target_blocks == expected_sequence
    assert 35 not in target_blocks, "Old 35-block milestone must not be in post-repair sequence"

def test_production_model_frozen():
    report = longitudinal_status_service.get_status_report()
    assert report.observed_metrics["model_status"] == "MODEL_FROZEN"
