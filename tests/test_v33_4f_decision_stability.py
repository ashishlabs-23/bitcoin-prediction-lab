"""
BTCognitive V33.4F — Decision Identity Stability & Polling Invariants Test Suite.
Verifies that:
1. An unchanged market snapshot produces identical decision_id across repeated calls.
2. An altered candle watermark or regime produces a distinct decision_id.
3. Material decision fields (action, reason, candidate setup) govern the hash.
4. Timestamps are stably anchored to the analysis snapshot.
"""

import json
from engine.regime_strategy_tournament import (
    _compute_stable_decision_id,
    formulate_smart_entry_decision
)

class TestV33_4F_Decision_Stability:
    def test_same_snapshot_produces_identical_decision_id(self):
        analysis_res = {
            "analysis_id": "ana_test_101",
            "timestamp_utc": "2026-11-01T20:00:00+00:00",
            "candle_watermark_hash": "wm_fixed_abc123",
            "market_regime": {"regime": "VOLATILITY_EXPANSION"},
            "shortlisted_candidates": [],
            "candidate_rejections": [],
            "reason": "Screen rejected 3 strategies"
        }
        dec_1 = formulate_smart_entry_decision(analysis_res, None)
        dec_2 = formulate_smart_entry_decision(analysis_res, None)
        
        # Invariant: Stable decision identity
        assert dec_1["decision_id"] == dec_2["decision_id"]
        assert dec_1["decision_timestamp_utc"] == dec_2["decision_timestamp_utc"]
        assert dec_1["action"] == dec_2["action"]
        assert dec_1["status"] == dec_2["status"]
        assert dec_1["reason"] == dec_2["reason"]

    def test_changed_watermark_produces_distinct_decision_id(self):
        base_res = {
            "analysis_id": "ana_test_101",
            "timestamp_utc": "2026-11-01T20:00:00+00:00",
            "market_regime": {"regime": "VOLATILITY_EXPANSION"},
            "shortlisted_candidates": []
        }
        res_a = {**base_res, "candle_watermark_hash": "wm_snapshot_A"}
        res_b = {**base_res, "candle_watermark_hash": "wm_snapshot_B"}
        
        dec_a = formulate_smart_entry_decision(res_a, None)
        dec_b = formulate_smart_entry_decision(res_b, None)
        
        assert dec_a["decision_id"] != dec_b["decision_id"]

    def test_changed_regime_produces_distinct_decision_id(self):
        base_res = {
            "analysis_id": "ana_test_101",
            "timestamp_utc": "2026-11-01T20:00:00+00:00",
            "candle_watermark_hash": "wm_snapshot_fixed",
            "shortlisted_candidates": []
        }
        res_vol = {**base_res, "market_regime": {"regime": "VOLATILITY_EXPANSION"}}
        res_trend = {**base_res, "market_regime": {"regime": "TRENDING_BULLISH"}}
        
        dec_vol = formulate_smart_entry_decision(res_vol, None)
        dec_trend = formulate_smart_entry_decision(res_trend, None)
        
        assert dec_vol["decision_id"] != dec_trend["decision_id"]

    def test_winner_decision_is_deterministic_and_strategy_aware(self):
        analysis_res = {
            "analysis_id": "ana_test_winner",
            "timestamp_utc": "2026-11-01T20:00:00+00:00",
            "candle_watermark_hash": "wm_winner_fixed",
            "market_regime": {"regime": "VOLATILITY_EXPANSION"},
            "shortlisted_candidates": [
                {
                    "strategy_id": "HTF_RANGE_EXPANSION_BREAKOUT",
                    "direction": "LONG",
                    "holding_horizon_hours": 24,
                    "proposed_geometry": {
                        "reference_entry_price": 76985.4,
                        "proposed_tp_price": 79200.0,
                        "proposed_sl_price": 75800.0,
                        "reward_usd": 2214.6,
                        "risk_usd": 1185.4,
                        "reward_risk_ratio": 1.868,
                        "anomaly_policy": "STRICT_ABSTAIN"
                    }
                }
            ]
        }
        tournament_res = {
            "final_verdict": "QUALIFIED_WINNER_FOUND",
            "tournament_id": "tourney_101",
            "tournament_winner": {
                "strategy_id": "HTF_RANGE_EXPANSION_BREAKOUT",
                "strategy_name": "HTF Range Expansion Breakout",
                "version": "1.0",
                "screen_7_of_10_detail": {
                    "tp_hits": 8,
                    "total_attempts": 10,
                    "wilson_ci_95": [0.49, 0.94]
                },
                "arm_2_strategy_plus_ai": {
                    "tp_first_rate": 0.65,
                    "total_opportunities": 85,
                    "wilson_ci_95": [0.54, 0.74],
                    "ai_incremental_improvement_pct": 5.2
                }
            }
        }
        dec_w1 = formulate_smart_entry_decision(analysis_res, tournament_res)
        dec_w2 = formulate_smart_entry_decision(analysis_res, tournament_res)
        
        assert dec_w1["status"] == "SMART_ENTRY_AVAILABLE"
        assert dec_w1["action"] == "TAKE_SIMULATED_TRADE_ELIGIBLE"
        assert dec_w1["decision_id"] == dec_w2["decision_id"]
        assert dec_w1["candidate_setup"]["strategy_id"] == "HTF_RANGE_EXPANSION_BREAKOUT"

