"""
tests/test_v33_1_entry_and_analysis_decoupling.py - Decoupled Entry & Analysis Positive-Path & Gating Tests
=============================================================================================================
Verifies Milestone V33.1 / V33.1A decoupled architecture:
1. Positive-path Market Intelligence generation (volatility term structure, regime, C2 envelope, excursions).
2. Stale data decoupling: Distinguishes current observations from cached historical observations.
3. 5-Question Trade Authorization: All 5 independent questions evaluated explicitly with PASS, FAIL, INSUFFICIENT_EVIDENCE.
4. Q2 Directional Evidence semantics: Insufficient evidence blocks eligibility; Q1, Q3, Q4, Q5 cannot override Q2.
5. Cost awareness: Retail execution friction (87 bps) prevents false trade eligibility.
6. Sample size & C2 calibration: N >= 30 is diagnostic minimum only; C2 coverage separated from trade probability.
7. User preference bias rejection guardrail: User intent cannot force trade approval.
8. Backward compatibility of integrated analyse workflow.
9. Permanent non-execution invariant: live_trading == DISABLED — ANALYSIS ONLY.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

from engine.decoupled_analysis_engine import decoupled_analysis_engine, DecoupledAnalysisEngine
from engine.regime_strategy_tournament import (
    analyse_current_market,
    execute_integrated_analyse_and_tournament,
)
from engine.range_forecast_service import RangeForecastService


@pytest.fixture(autouse=True)
def prevent_persistent_forecast_writes(monkeypatch):
    monkeypatch.setattr(RangeForecastService, "_persist_forecast", lambda *_: None)


def _build_synthetic_closed_candles(n_bars: int = 300, end_age_hours: float = 0.5) -> pd.DataFrame:
    """Helper to generate continuous closed hourly candles with controllable age."""
    now = datetime.now(timezone.utc)
    end_time = now - timedelta(hours=end_age_hours)
    timestamps = [end_time - timedelta(hours=(n_bars - 1 - i)) for i in range(n_bars)]

    # Deterministic price path (starting at $85,000)
    np.random.seed(42)
    returns = np.random.normal(0.0001, 0.008, n_bars)
    prices = 85000.0 * np.exp(np.cumsum(returns))

    candles = []
    for i in range(n_bars):
        close_p = float(prices[i])
        open_p = float(prices[i - 1]) if i > 0 else close_p
        high_p = max(open_p, close_p) * (1.0 + abs(float(np.random.normal(0, 0.003))))
        low_p = min(open_p, close_p) * (1.0 - abs(float(np.random.normal(0, 0.003))))
        candles.append({
            "timestamp": timestamps[i].isoformat(),
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": round(150.0 + abs(float(np.random.normal(0, 30))), 2),
            "is_closed": True
        })

    return pd.DataFrame(candles)


class TestV331DecoupledAnalysisArchitecture:
    """Positive-path and decoupled governance test suite for V33.1 & V33.1A."""

    def test_positive_path_market_intelligence_generation(self):
        """
        Positive-Path Test:
        Verifies that given valid, fresh closed candles, Market Intelligence Report
        generates complete volatility term structure, regime, C2 envelope, and excursions.
        """
        df = _build_synthetic_closed_candles(n_bars=300, end_age_hours=0.5)
        live_price = float(df["close"].iloc[-1])

        res = decoupled_analysis_engine.execute_decoupled_analysis(
            df_1h=df,
            live_price=live_price,
            enforce_freshness=False,
            max_age_hours=3.0
        )

        assert "market_intelligence" in res
        intel = res["market_intelligence"]
        assert intel["status"] == "SUCCESS"
        assert intel["current_market_assessment"] == "AVAILABLE"
        assert intel["current_price"] == live_price
        assert intel["last_observed_candle_price"] == live_price

        # Volatility term structure assertions
        ts = intel["volatility_term_structure"]
        assert ts["rv_1h_pct"] > 0
        assert ts["rv_4h_pct"] > 0
        assert ts["rv_24h_pct"] > 0
        assert ts["rv_7d_pct"] > 0
        assert ts["rv_30d_pct"] > 0
        assert ts["vol_ratio_1h_24h"] > 0
        assert ts["curve_shape"] in ["INVERTED_EXPANSION", "FLAT", "CONTANGO_COMPRESSION"]

        # Market regime assertions
        reg = intel["volatility_regime"]
        assert "regime" in reg
        assert reg["bollinger_band_width_pct"] > 0
        assert reg["wilder_adx_14"] >= 0
        assert reg["atr_14_usd"] > 0

        # C2 remains disabled until a verifiable calibration artifact exists.
        env = intel["conformal_risk_envelope_7d"]
        assert env["status"] == "UNAVAILABLE"
        assert env["calibration_status"] == "DISABLED_BY_GOVERNANCE"
        assert env["nominal_target_coverage_pct"] is None
        assert env["point_forecast_variance"] is None
        assert env["conformal_lower_variance"] is None
        assert env["conformal_upper_variance"] is None

        # Excursion estimates assertions (Manager Issue 3)
        exc = intel["excursion_estimates_24h"]
        assert exc["favourable_excursion_upper"]["p10_price"] < exc["favourable_excursion_upper"]["p90_price"]
        assert exc["adverse_excursion_lower"]["p90_price"] < exc["adverse_excursion_lower"]["p10_price"]
        assert exc["expected_favourable_excursion_upper_p50"] > 0
        assert exc["expected_adverse_excursion_lower_p50"] > 0

    def test_stale_data_decoupling_preserves_market_intelligence_while_blocking_trade(self):
        """
        Decoupled Freshness Test (Manager Issue 2):
        Verifies that when market data is stale (> 3.0h), Market Intelligence Report
        distinguishes current observations from cached historical observations:
        - current_market_assessment is UNAVAILABLE
        - current_price is None (does NOT silently present stale close as live price)
        - last_observed_candle_price is preserved with timestamp
        - historical volatility and risk envelope are AVAILABLE_WITH_TIMESTAMP
        - Trade Authorization is locked to ABSTAIN.
        """
        df_stale = _build_synthetic_closed_candles(n_bars=300, end_age_hours=12.0)
        live_price = float(df_stale["close"].iloc[-1])

        res = decoupled_analysis_engine.execute_decoupled_analysis(
            df_1h=df_stale,
            live_price=live_price,
            enforce_freshness=True,
            max_age_hours=3.0
        )

        intel = res["market_intelligence"]
        assert intel["status"] == "SUCCESS"
        assert intel["data_freshness"]["is_fresh"] is False
        assert intel["data_freshness"]["is_stale"] is True
        assert intel["data_freshness"]["observed_age_hours"] >= 11.0
        assert intel["current_market_assessment"] == "UNAVAILABLE"
        assert intel["current_price"] is None
        assert intel["last_observed_candle_price"] == live_price
        assert intel["historical_volatility_analysis"] == "AVAILABLE"
        assert intel["historical_risk_envelope"] == "UNVALIDATED_HEURISTIC_WITH_TIMESTAMP"
        assert len(intel["data_quality_warnings"]) >= 1
        assert "STALE_DATA_WARNING" in intel["data_quality_warnings"][0]

        # Output B (Trade Authorization) must FAIL CLOSED to ABSTAIN
        auth = res["trade_authorization"]
        assert auth["final_decision"] == "ABSTAIN"
        assert auth["actionable_recommendation"] == "NO_TRADE"
        assert "stale market data" in auth["decision_summary"].lower()

        # All 5 questions must indicate BLOCKED_STALE with state == FAIL
        for q_name, q_data in auth["five_question_evaluation"].items():
            assert q_data["state"] == "FAIL"
            assert q_data["passed"] is False
            if q_name == "question_5_confidence_calibration":
                assert q_data["status"] == "CALIBRATION_UNAVAILABLE"
            else:
                assert q_data["status"] == "BLOCKED_STALE"

    def test_five_question_trade_authorization_evaluation(self):
        """
        5-Question Evaluation Contract Test (Manager Issues 1, 3, 4):
        Verifies that all five questions explicitly return PASS, FAIL, or INSUFFICIENT_EVIDENCE states.
        """
        df = _build_synthetic_closed_candles(n_bars=300, end_age_hours=0.5)
        live_price = float(df["close"].iloc[-1])

        res = decoupled_analysis_engine.execute_decoupled_analysis(
            df_1h=df,
            live_price=live_price,
            max_age_hours=3.0
        )

        auth = res["trade_authorization"]
        questions = auth["five_question_evaluation"]

        assert set(questions.keys()) == {
            "question_1_market_regime",
            "question_2_directional_evidence",
            "question_3_entry_location",
            "question_4_execution_economics",
            "question_5_confidence_calibration"
        }

        # Question 1: Regime
        q1 = questions["question_1_market_regime"]
        assert q1["state"] in ["PASS", "FAIL"]
        assert isinstance(q1["passed"], bool)

        # Question 2: Directional Evidence (Must be INSUFFICIENT_EVIDENCE, not FAIL)
        q2 = questions["question_2_directional_evidence"]
        assert q2["state"] == "INSUFFICIENT_EVIDENCE"
        assert q2["status"] == "INSUFFICIENT_EVIDENCE"
        assert q2["passed"] is False
        assert q2["research_authorization_state"] == "CURRENTLY_UNAUTHORIZED_PENDING_NEW_VALIDATED_EVIDENCE"

        # Question 3: Entry Location
        q3 = questions["question_3_entry_location"]
        assert "structural_location_quality" in q3
        assert "support_price" in q3
        assert "resistance_price" in q3
        assert "Never equate location quality with probability of profit" in q3["anti_conflation_notice"]

        # Question 4: Execution Economics
        q4 = questions["question_4_execution_economics"]
        assert q4["state"] in ["PASS", "FAIL"]
        assert "friction_breakdown" in q4

        # Question 5: Confidence & Calibration
        q5 = questions["question_5_confidence_calibration"]
        assert q5["diagnostic_sample_floor_n"] == 30
        assert q5["sample_size_classification"] == "DIAGNOSTIC_MINIMUM_ONLY — NOT_A_VALIDATION_THRESHOLD"
        assert q5["calibration_status"] == "UNAVAILABLE"
        assert q5["effective_sample_size_estimate_n_eff"] is None

        # Final decision must default to ABSTAIN when directional evidence is insufficient
        assert auth["final_decision"] == "ABSTAIN"
        assert auth["actionable_recommendation"] == "NO_TRADE"

    def test_q2_directional_evidence_blocks_override(self):
        """
        Governance Invariant Test (Manager Issue 1):
        Verifies that even if Q1, Q3, Q4, and Q5 pass technical checks,
        Q2 INSUFFICIENT_EVIDENCE strictly prevents trade eligibility (ABSTAIN).
        Q1, Q3, Q4, Q5 CANNOT override Q2.
        """
        df = _build_synthetic_closed_candles(n_bars=300, end_age_hours=0.5)
        live_price = float(df["close"].iloc[-1])

        # Evaluate with 0-cost venue to pass Q4 economics check
        auth = decoupled_analysis_engine.evaluate_five_question_trade_authorization(
            df_closed=df,
            live_price=live_price,
            market_intel=decoupled_analysis_engine.compute_market_intelligence_report(df, live_price),
            cost_venue="BINANCE_VIP0_MAKER"  # minimal friction
        )

        q2 = auth["five_question_evaluation"]["question_2_directional_evidence"]
        assert q2["state"] == "INSUFFICIENT_EVIDENCE"

        # Final decision must remain ABSTAIN
        assert auth["final_decision"] == "ABSTAIN"
        assert auth["actionable_recommendation"] == "NO_TRADE"
        assert "Q2 Directional Evidence is INSUFFICIENT_EVIDENCE" in auth["decision_summary"]
        assert "Individual checks Q1, Q3, Q4, Q5 cannot override" in auth["decision_summary"]

    def test_execution_friction_cost_awareness(self):
        """
        Cost Awareness Test (Manager Issues 3, 4):
        Verifies that at Coinbase Retail friction (87 bps), Question 4 fails with FAILS_FEE_DRAG,
        ensuring a favorable market structure cannot conceal negative net trading economics.
        """
        df = _build_synthetic_closed_candles(n_bars=300, end_age_hours=0.5)
        live_price = float(df["close"].iloc[-1])

        auth = decoupled_analysis_engine.evaluate_five_question_trade_authorization(
            df_closed=df,
            live_price=live_price,
            market_intel=decoupled_analysis_engine.compute_market_intelligence_report(df, live_price),
            cost_venue="COINBASE_ADVANCED_87BPS"
        )

        assert auth["execution_friction_assumed_bps"] == 87.0
        q4 = auth["five_question_evaluation"]["question_4_execution_economics"]
        assert q4["state"] == "FAIL"
        assert q4["status"] == "FAILS_FEE_DRAG"
        assert q4["passed"] is False
        assert q4["net_expected_value_bps"] < 0
        assert "87.0 bps" in q4["explanation"]

    def test_user_preference_bias_rejection_guardrail(self):
        """
        User Bias Rejection Test:
        Verifies that when a user specifies intent (e.g. LONG), but economic/evidence gates fail,
        the system safely rejects the user bias, flags user_bias_rejected=True, and ABSTAINS.
        """
        df = _build_synthetic_closed_candles(n_bars=300, end_age_hours=0.5)
        live_price = float(df["close"].iloc[-1])

        auth = decoupled_analysis_engine.evaluate_five_question_trade_authorization(
            df_closed=df,
            live_price=live_price,
            market_intel=decoupled_analysis_engine.compute_market_intelligence_report(df, live_price),
            user_intent_direction="LONG",
            cost_venue="COINBASE_ADVANCED_87BPS"
        )

        assert auth["final_decision"] == "ABSTAIN"
        assert auth["user_bias_rejected"] is True
        assert "REJECTED by governance guardrails" in auth["decision_summary"]

    def test_integrated_workflow_backward_compatibility(self):
        """
        Backward Compatibility Test:
        Verifies that execute_integrated_analyse_and_tournament bundles both
        market_intelligence and trade_authorization while preserving all legacy keys.
        """
        df = _build_synthetic_closed_candles(n_bars=300, end_age_hours=0.5)
        live_price = float(df["close"].iloc[-1])

        res = execute_integrated_analyse_and_tournament(
            df_1h=df,
            live_price=live_price,
            enforce_freshness=False
        )

        # Legacy fields preserved
        assert res["is_read_only"] is True
        assert res["attempts_created"] == 0
        assert "candle_watermark" in res
        assert "market_regime" in res
        assert "shortlisted_candidates" in res
        assert "tournament" in res
        assert "smart_entry_decision" in res

        # New decoupled fields attached
        assert "market_intelligence" in res
        assert res["market_intelligence"]["status"] == "SUCCESS"
        assert "trade_authorization" in res
        assert res["trade_authorization"]["final_decision"] in ["ABSTAIN", "ELIGIBLE"]
        assert res["trade_authorization"]["live_trading"] == "DISABLED — ANALYSIS ONLY"

    def test_api_tournament_analyse_http_contract_decoupling(self):
        """
        API Contract Test (Manager Issue 5):
        Verifies that POST /api/tournament/analyse returns HTTP 200 with both
        market_intelligence and trade_authorization in the response schema.
        """
        from fastapi.testclient import TestClient
        from api.server import app

        client = TestClient(app)
        df = _build_synthetic_closed_candles(n_bars=300, end_age_hours=0.5)
        candles_payload = df.to_dict(orient="records")
        aligned_last_open = pd.Timestamp.now(tz="UTC").floor("h") - timedelta(hours=1)
        for index, candle in enumerate(candles_payload):
            candle["timestamp"] = (
                aligned_last_open - timedelta(hours=len(candles_payload) - index - 1)
            ).isoformat()
            candle["is_closed"] = True

        resp = client.post("/api/tournament/analyse", json={
            "data_source": "DETERMINISTIC_FIXTURE",
            "candles": candles_payload,
            "auto_tournament": True,
            "enforce_freshness": False
        })
        assert resp.status_code == 200
        data = resp.json()

        assert "market_intelligence" in data
        assert data["market_intelligence"]["status"] == "SUCCESS"
        assert "volatility_term_structure" in data["market_intelligence"]
        assert "conformal_risk_envelope_7d" in data["market_intelligence"]

        assert "trade_authorization" in data
        assert data["trade_authorization"]["final_decision"] in ["ABSTAIN", "ELIGIBLE"]
        assert data["trade_authorization"]["live_trading"] == "DISABLED — ANALYSIS ONLY"
        assert data["is_read_only"] is True
        assert data["attempts_created"] == 0

    def test_live_trading_permanently_disabled(self):
        """Governance assertion: Live trading is permanently DISABLED across all decoupled outputs."""
        df = _build_synthetic_closed_candles(n_bars=300, end_age_hours=0.5)
        live_price = float(df["close"].iloc[-1])

        res = decoupled_analysis_engine.execute_decoupled_analysis(
            df_1h=df,
            live_price=live_price
        )

        assert res["live_trading"] == "DISABLED — ANALYSIS ONLY"
        assert res["trade_authorization"]["live_trading"] == "DISABLED — ANALYSIS ONLY"
        assert res["is_read_only"] is True
        assert res["attempts_created"] == 0
