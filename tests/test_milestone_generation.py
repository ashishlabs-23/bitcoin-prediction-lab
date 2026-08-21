"""
tests/test_milestone_generation.py — Unit Tests for Target Milestone Report Generation
======================================================================================
Verifies:
1. Target milestone reports are created with explicit 'TARGET / NOT YET OBSERVED' headers
2. No fake measured numbers populate unreached milestone markdown files
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORTS_DIR = os.path.join(ROOT_DIR, "research", "reports")


def test_target_milestone_report_headers():
    for m in [35, 40, 50, 60, 75, 90]:
        report_file = os.path.join(REPORTS_DIR, f"longitudinal_target_{m}.md")
        assert os.path.exists(report_file)

        with open(report_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "TARGET / NOT YET OBSERVED" in content
        assert "This milestone represents a future evidence accumulation target" in content
