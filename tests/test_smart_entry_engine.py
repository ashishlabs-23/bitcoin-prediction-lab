import numpy as np

from engine.smart_entry_engine import SmartEntryDecisionEngine


def test_smart_entry_engine_builds_long_candidate():
    closes = np.linspace(61000.0, 65000.0, 40)
    highs = closes * 1.01
    lows = closes * 0.99
    candles = [
        {
            "timestamp_utc": f"2026-10-01T00:{i:02d}:00Z" if i < 60 else f"2026-10-01T01:{i % 60:02d}:00Z",
            "open": float(c),
            "high": float(h),
            "low": float(l),
            "close": float(c),
        }
        for i, (c, h, l) in enumerate(zip(closes, highs, lows))
    ]

    engine = SmartEntryDecisionEngine()
    result = engine.evaluate_market(
        live_price=65000.0,
        candles=candles,
        enabled_indicators=["ofi", "hawkes", "vpin", "rv_5m", "liquidations"],
        market_snapshot={"ofi": 0.85, "hawkes": 2.5, "vpin": 0.18, "spread_bps": 2.0, "depth_score": 0.82, "is_expansion": True},
        regime="VOL_EXPANDING",
        c2_health="CALIBRATED",
        user_direction_preference="AUTO",
    )

    assert result["status"] == "ABSTAIN"
    assert result["decision_action"] == "ABSTAIN"
    assert "NO_VALIDATED_EDGE_ABSTAIN" in result["primary_reason"]
    assert result["first_passage_geometry_baseline"] is not None
    assert "p_tp" in result["first_passage_geometry_baseline"]
    assert result["candidate"] is None
    assert result["execution_authorization"] == "DISABLED — ANALYSIS ONLY"


def test_smart_entry_engine_abstains_when_inputs_invalid():
    engine = SmartEntryDecisionEngine()
    result = engine.evaluate_market(live_price=0.0, market_snapshot={})
    assert result["status"] == "ABSTAIN"
    assert result["decision_action"] == "ABSTAIN"
    assert result["candidate"] is None
    assert result["resolution"] is None
