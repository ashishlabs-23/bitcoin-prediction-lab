"""
tests/test_directional_evidence.py — Unit Tests for Directional Evidence Synthesizer
=====================================================================================
Verifies:
1. Strict separation of 5m Hawkes shadow direction from 24h structural forecast
2. Invariant: 24h structural direction is NO_MEASURABLE_EDGE
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.directional_evidence import directional_evidence_service, DirectionalEvidenceSummary


def test_directional_evidence_synthesis():
    summary = directional_evidence_service.synthesize_directional_evidence(
        hawkes_intensity_ratio=1.15,
        hawkes_direction="BULLISH_PRESSURE"
    )

    assert isinstance(summary, DirectionalEvidenceSummary)
    assert summary.horizon_5m_direction == "BULLISH_PRESSURE"
    assert summary.horizon_5m_status == "VALIDATED_SHADOW_MODEL"
    assert summary.horizon_24h_direction == "NO_MEASURABLE_EDGE"
    assert summary.horizon_24h_status == "VALIDATED_PRODUCTION_RANGE_SYSTEM"
