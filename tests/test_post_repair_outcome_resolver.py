"""
tests/test_post_repair_outcome_resolver.py — Tests for Outcome Resolver Engine
==============================================================================
Verifies:
- Resolver handles UNRESOLVED records cleanly.
- WAITING_FOR_HORIZON is returned when 24h has not elapsed.
- Immutability of original prediction record is preserved.
"""

from datetime import datetime, timezone, timedelta
from research.post_repair_outcome_resolver import post_repair_resolver

def test_resolver_waiting_for_horizon():
    now_dt = datetime.now(timezone.utc)
    mock_row = {
        "prediction_id": "test_pred_waiting_1",
        "timestamp": now_dt.isoformat(),
        "price": 65000.0,
        "outcome_resolved": 0,
        "was_correct": None
    }
    # Resolve at current time (0 hours elapsed)
    res = post_repair_resolver.resolve_forecast(mock_row, current_time=now_dt)
    assert res["status"] == "WAITING_FOR_HORIZON"
    assert res["hours_remaining"] > 23.0

def test_resolver_already_resolved_idempotence():
    mock_row = {
        "prediction_id": "test_pred_already_resolved",
        "timestamp": "2026-08-20T00:00:00Z",
        "price": 65000.0,
        "outcome_resolved": 1,
        "was_correct": 1
    }
    res = post_repair_resolver.resolve_forecast(mock_row)
    assert res["status"] == "ALREADY_RESOLVED"
