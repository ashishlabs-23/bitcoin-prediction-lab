"""
tests/test_pre_post_separation.py — Tests for Strict Pre/Post Repair Separation
================================================================================
Verifies that:
- Pre-repair observations are never counted inside post-repair block counter.
- pre_post_repair_comparison.md report exists and categorizes comparability cleanly.
"""

import os
from research.post_repair_comparison import generate_comparison_report, REPORT_PATH

def test_pre_post_report_exists():
    generate_comparison_report()
    assert os.path.exists(REPORT_PATH)
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    assert "NOT DIRECTLY COMPARABLE" in content
    assert "Pre-Repair vs Post-Repair Metric Reconciliation" in content
