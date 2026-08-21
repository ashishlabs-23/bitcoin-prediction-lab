"""
tests/test_resolution_health.py — Tests for Resolution Health Endpoint & Data Freshness
========================================================================================
Verifies:
- get_resolution_health returns well-formed dictionary with integer counts and freshness state.
"""

from research.post_repair_outcome_resolver import post_repair_resolver

def test_resolution_health_payload():
    h = post_repair_resolver.get_resolution_health()
    assert isinstance(h, dict)
    assert "unresolved_forecasts" in h
    assert "ready_to_resolve" in h
    assert "data_freshness" in h
    assert h["unresolved_forecasts"] >= 0
    assert h["ready_to_resolve"] >= 0
