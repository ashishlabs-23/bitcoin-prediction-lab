"""
tests/test_longitudinal_status.py — Unit Tests for Longitudinal Status Protocol
================================================================================
Verifies:
1. Complete separation of OBSERVED metrics from TARGET milestones
2. Progress percentage, next milestone block, and governance status
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.longitudinal_status import longitudinal_status_service, LongitudinalStatusReport


def test_longitudinal_status_report_structure():
    status = longitudinal_status_service.get_status_report()

    assert isinstance(status, LongitudinalStatusReport)
    assert status.observed_blocks == 35
    assert status.target_blocks == 90
    assert status.next_milestone_block == 40
    assert status.progress_pct == 38.9
    assert status.observed_metrics["mfe_error_pct"] == 0.3970
    assert len(status.milestone_targets) == 5
    assert status.milestone_targets[0]["status"] == "NOT_YET_OBSERVED"
