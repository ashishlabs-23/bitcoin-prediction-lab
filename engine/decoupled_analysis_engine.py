"""
engine/decoupled_analysis_engine.py — Decoupled Market Intelligence & Trade Authorization Engine
=================================================================================================
Implements the BTCognitive V33.1 / V33.1A decoupled analysis architecture:
1. Output A: Market Intelligence Report (Available on demand, succeeds even when trading is blocked)
   - Last observed BTC candle price and data freshness status
   - Distinguishes current market assessment from cached historical context
   - Volatility term structure (1h, 4h, 24h, 7d, 30d annualized)
   - Volatility expansion / compression state (ADX, ATR, BBW, EMAs)
   - 7-day C2 risk envelope is unavailable until a verifiable calibration artifact exists
   - 24-hour P10..P90 favourable (MFE) and adverse (MAE) excursion estimates
   - Calibration health and explicit data quality warnings (when stale)

2. Output B: Trade Authorization (Strictly gated, evaluated across Five Independent Questions)
   - Question 1: Market Regime (Trending, ranging, compressing, expanding?)
   - Question 2: Directional Evidence (Currently unauthorized pending new validated evidence)
   - Question 3: Entry Location (Structural support/resistance & ATR distance; NOT alpha)
   - Question 4: Risk/Reward & Execution Economics (Net EV > 0 after 24-87 bps friction)
   - Question 5: Confidence & Calibration (N >= 30 is diagnostic minimum only, C2 containment)
   - Final Decision: ELIGIBLE, REJECTED, or ABSTAIN (Defaults safely to ABSTAIN)

Strict Invariants:
- A blocked trade recommendation NEVER suppresses or blanks market intelligence.
- Live trading is permanently DISABLED (analysis & risk advisory only).
- Stale data issues an explicit warning and gates trading, while serving valid historical intelligence.
- Zero simulated trade creation (attempts_created = 0, is_read_only = True).
- Q1, Q3, Q4, Q5 CANNOT override Q2 directional insufficiency.
"""

import os
import sys
import math
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from engine.execution_cost_model import ExecutionCostModel
from engine.regime_strategy_tournament import (
    MarketRegimeClassifier,
    check_data_freshness_and_gaps,
    _validate_hourly_candles,
    _closed_candle_window_hash
)
from engine.range_forecast_service import RangeForecastService


def _validated_bollinger_bounds(regime_info: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
    try:
        raw_bounds = (regime_info["bb_lower"], regime_info["bb_mid"], regime_info["bb_upper"])
        if any(isinstance(value, bool) for value in raw_bounds):
            return None
        lower, middle, upper = (float(value) for value in raw_bounds)
    except (KeyError, TypeError, ValueError, OverflowError):
        return None

    if not all(math.isfinite(value) and value > 0.0 for value in (lower, middle, upper)):
        return None
    if not lower < middle < upper:
        return None
    return lower, middle, upper


class DecoupledAnalysisEngine:
    """
    Decoupled Market Intelligence and 5-Question Trade Authorization Engine.
    """

    def __init__(self):
        self.range_service = RangeForecastService()

    def compute_market_intelligence_report(
        self,
        df_closed: pd.DataFrame,
        live_price: Optional[float] = None,
        max_age_hours: float = 3.0,
        dataset_fingerprint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Computes Output A: Comprehensive Market Intelligence Report.
        Succeeds independently of trade authorization or execution status.
        Distinguishes current observations from cached historical observations.
        """
        now_utc = datetime.now(timezone.utc)
        now_iso = now_utc.isoformat()

        if df_closed is None or df_closed.empty or len(df_closed) < 24:
            return {
                "status": "UNAVAILABLE",
                "timestamp_utc": now_iso,
                "reason": "Insufficient closed candle history (minimum 24 bars required).",
                "current_market_assessment": "UNAVAILABLE",
                "current_price": None,
                "last_observed_candle_price": round(float(live_price), 2) if (live_price is not None and live_price > 0) else None,
                "last_observed_candle_time": None,
                "historical_volatility_analysis": "UNAVAILABLE",
                "historical_risk_envelope": "UNAVAILABLE",
                "data_freshness": None,
                "volatility_term_structure": None,
                "volatility_regime": None,
                "conformal_risk_envelope_7d": None,
                "excursion_estimates_24h": None,
                "data_quality_warnings": ["INSUFFICIENT_DATA_BARS"]
            }

        # 1. Price and Timestamp Anchor
        last_row = df_closed.iloc[-1]
        ts_col = "timestamp" if "timestamp" in df_closed.columns else ("timestamp_utc" if "timestamp_utc" in df_closed.columns else df_closed.index.name)
        if ts_col and ts_col in df_closed.columns:
            last_ts = pd.to_datetime(last_row[ts_col], utc=True).isoformat()
        else:
            last_ts = now_iso

        last_observed_close = float(last_row["close"])
        ref_price = float(live_price) if (live_price is not None and live_price > 0) else last_observed_close

        # 2. Data Freshness & Watermark
        freshness_res = check_data_freshness_and_gaps(
            df_closed,
            max_age_hours=max_age_hours,
            dataset_fingerprint=dataset_fingerprint
        )
        is_fresh = bool(freshness_res.get("is_fresh", False))
        observed_age_h = float(freshness_res.get("observed_age_seconds", 0.0)) / 3600.0

        data_warnings = []
        if not is_fresh:
            data_warnings.append(
                f"STALE_DATA_WARNING: Closed candles are {observed_age_h:.1f}h old (exceeds {max_age_hours:.1f}h operational limit). "
                f"Market intelligence represents historical/cached context, NOT live market conditions. "
                f"Current-market assessment is UNAVAILABLE. Trade authorization is locked to ABSTAIN."
            )
        if freshness_res.get("has_candle_gaps", False):
            gap_cnt = freshness_res.get("candle_gap_count", 0)
            data_warnings.append(f"CANDLE_GAP_WARNING: Detected {gap_cnt} candle gaps in recent evaluation window.")

        # 3. Volatility Term Structure (Realized Volatility Annualized %)
        closes = df_closed["close"].astype(float).values
        returns = np.diff(np.log(closes))

        # Hourly returns annualized factor: sqrt(8760)
        ann_factor = math.sqrt(8760.0) * 100.0

        def calc_rv(window: int) -> float:
            if len(returns) < window:
                sub = returns
            else:
                sub = returns[-window:]
            if len(sub) == 0:
                return 0.0
            var = float(np.mean(sub**2))
            return round(math.sqrt(var) * ann_factor, 2)

        rv_1h = round(abs(float(returns[-1])) * ann_factor, 2) if len(returns) > 0 else 0.0
        rv_4h = calc_rv(4)
        rv_24h = calc_rv(24)
        rv_7d = calc_rv(168)
        rv_30d = calc_rv(min(len(returns), 720))

        vol_ratio_1h_24h = round(rv_1h / rv_24h, 3) if rv_24h > 0 else 1.0

        vol_term_structure = {
            "rv_1h_pct": rv_1h,
            "rv_4h_pct": rv_4h,
            "rv_24h_pct": rv_24h,
            "rv_7d_pct": rv_7d,
            "rv_30d_pct": rv_30d,
            "vol_ratio_1h_24h": vol_ratio_1h_24h,
            "curve_shape": "INVERTED_EXPANSION" if vol_ratio_1h_24h > 1.25 else ("FLAT" if vol_ratio_1h_24h >= 0.85 else "CONTANGO_COMPRESSION"),
            "measurement_horizon_hours": 720,
            "annualization_convention": "Hourly log-returns scaled by sqrt(8760)"
        }

        # 4. Volatility Regime & Market Structure
        regime_res = MarketRegimeClassifier.classify(df_closed)
        regime_state = regime_res.get("regime", "UNKNOWN")
        bbw_raw = float(regime_res.get("bbw") or regime_res.get("bb_width") or 0.0)
        bbw_pct = round(bbw_raw * 100.0, 2)
        adx_val = round(float(regime_res.get("adx") or 0.0), 2)
        atr_usd = round(float(regime_res.get("atr") or 0.0), 2)
        trend_dir = regime_res.get("trend") or "NEUTRAL"
        bollinger_bounds = _validated_bollinger_bounds(regime_res)

        volatility_regime = {
            "regime": regime_state,
            "is_expansion": "EXPANSION" in regime_state.upper() or "TREND" in regime_state.upper(),
            "bollinger_band_width_pct": bbw_pct,
            "wilder_adx_14": adx_val,
            "trend_strength": "STRONG_TREND" if adx_val >= 25.0 else ("WEAK_TREND" if adx_val >= 18.0 else "CHOP_OR_COMPRESSION"),
            "atr_14_usd": atr_usd,
            "trend_direction": trend_dir,
            "bb_mid": round(bollinger_bounds[1], 2) if bollinger_bounds else None,
            "bb_upper": round(bollinger_bounds[2], 2) if bollinger_bounds else None,
            "bb_lower": round(bollinger_bounds[0], 2) if bollinger_bounds else None,
            "bollinger_bounds_status": "AVAILABLE" if bollinger_bounds else "UNAVAILABLE",
            "bollinger_bounds_reason_code": None if bollinger_bounds else "MISSING_OR_INVALID_BOLLINGER_BOUNDS",
            "evaluation_note": "Regime indicates volatility dynamics; does NOT imply directional trade probability."
        }

        # C2 is disabled by governance; no calibrated envelope is exposed.
        conformal_envelope_7d = {
            "status": "UNAVAILABLE",
            "calibration_status": "DISABLED_BY_GOVERNANCE",
            "reason_code": "C2_DISABLED",
            "explanation": "C2 is disabled; no calibrated 7-day risk envelope is available.",
            "point_forecast_variance": None,
            "point_forecast_volatility_pct": None,
            "conformal_lower_variance": None,
            "conformal_upper_variance": None,
            "conformal_lower_volatility_pct": None,
            "conformal_upper_volatility_pct": None,
            "nominal_target_coverage_pct": None,
            "uncertainty_engine": "C2 DISABLED"
        }

        # 6. Expected 24h Excursion Estimates (MFE / MAE Price Bounds)
        vol_24h_dec = float(rv_24h / (100.0 * math.sqrt(365.0)))
        range_fc = self.range_service.generate_forecast(
            current_price=ref_price,
            vol_24h=vol_24h_dec,
            features={"vol_24h": vol_24h_dec, "vol_ratio_1h_24h": vol_ratio_1h_24h, "rsi_14": 50.0},
            market_regime=regime_state
        )

        excursion_estimates_24h = {
            "horizon": "24h",
            "favourable_excursion_upper": {
                "p10_price": round(range_fc.upper_p10, 2),
                "p50_price": round(range_fc.upper_p50, 2),
                "p90_price": round(range_fc.upper_p90, 2),
                "p50_pct": round(((range_fc.upper_p50 - ref_price) / ref_price) * 100.0, 2),
                "p90_pct": round(((range_fc.upper_p90 - ref_price) / ref_price) * 100.0, 2)
            },
            "adverse_excursion_lower": {
                "p10_price": round(range_fc.lower_p10, 2),
                "p50_price": round(range_fc.lower_p50, 2),
                "p90_price": round(range_fc.lower_p90, 2),
                "p50_pct": round(((ref_price - range_fc.lower_p50) / ref_price) * 100.0, 2),
                "p90_pct": round(((ref_price - range_fc.lower_p90) / ref_price) * 100.0, 2)
            },
            "expected_favourable_excursion_upper_p50": round(range_fc.upper_p50, 2),
            "expected_adverse_excursion_lower_p50": round(range_fc.lower_p50, 2),
            "mondrian_scaling_factor": round(float(np.clip(1.0 + 0.35 * (vol_ratio_1h_24h - 1.0), 0.85, 1.45)), 3),
            "status": "UNVALIDATED_HEURISTIC",
            "calibration_status": "UNAVAILABLE",
            "anti_conflation_notice": "Bounds use fixed multipliers and are not calibrated empirical quantiles or a forecast of future trade profit."
        }

        # Distinguish current market assessment from cached historical context
        current_market_assessment = "AVAILABLE" if is_fresh else "UNAVAILABLE"
        display_current_price = round(ref_price, 2) if is_fresh else None
        historical_risk_envelope = "UNVALIDATED_HEURISTIC" if is_fresh else "UNVALIDATED_HEURISTIC_WITH_TIMESTAMP"

        return {
            "status": "SUCCESS",
            "calculation_status": "SUCCESS",
            "data_freshness_status": "FRESH" if is_fresh else "MARKET_DATA_STALE",
            "setup_evaluation_eligibility": "ELIGIBLE" if is_fresh else "INELIGIBLE_DATA_STALE",
            "data_age_hours": round(observed_age_h, 2),
            "last_observed_timestamp_utc": last_ts,
            "timestamp_utc": now_iso,
            "current_market_assessment": current_market_assessment,
            "current_price": display_current_price,
            "last_observed_candle_price": round(last_observed_close, 2),
            "last_observed_candle_time": last_ts,
            "historical_volatility_analysis": "AVAILABLE",
            "historical_risk_envelope": historical_risk_envelope,
            "data_freshness": {
                "is_fresh": is_fresh,
                "is_stale": not is_fresh,
                "observed_age_hours": round(observed_age_h, 2),
                "max_allowable_age_hours": max_age_hours,
                "has_gaps": freshness_res.get("has_candle_gaps", False),
                "gap_count": freshness_res.get("candle_gap_count", 0),
                "total_closed_candles": len(df_closed),
                "freshness_warning": data_warnings[0] if data_warnings else None
            },
            "volatility_term_structure": vol_term_structure,
            "volatility_regime": volatility_regime,
            "conformal_risk_envelope_7d": conformal_envelope_7d,
            "excursion_estimates_24h": excursion_estimates_24h,
            "calibration_health_state": "UNAVAILABLE",
            "calibration_status": "UNAVAILABLE",
            "data_quality_warnings": data_warnings
        }

    def evaluate_five_question_trade_authorization(
        self,
        df_closed: pd.DataFrame,
        live_price: float,
        market_intel: Dict[str, Any],
        user_intent_direction: Optional[str] = None,
        cost_venue: str = "COINBASE_ADVANCED_87BPS",
        max_age_hours: float = 3.0
    ) -> Dict[str, Any]:
        """
        Computes Output B: 5-Question Explainable Trade Authorization Gate.
        A candidate trade is ELIGIBLE only when ALL 5 mandatory questions PASS.
        Explicitly distinguishes PASS, FAIL, and INSUFFICIENT_EVIDENCE states.
        Q1, Q3, Q4, Q5 CANNOT override Q2 directional insufficiency.
        """
        eval_ts = datetime.now(timezone.utc).isoformat()
        is_fresh = market_intel.get("data_freshness", {}).get("is_fresh", False)
        observed_age_h = market_intel.get("data_freshness", {}).get("observed_age_hours", 0.0)

        # Execution Drag from ExecutionCostModel
        drag_bps = ExecutionCostModel.get_round_trip_friction_bps(venue=cost_venue)

        # ---------------------------------------------------------------------
        # Question 1: Market Regime
        # ---------------------------------------------------------------------
        regime_info = market_intel.get("volatility_regime") or {}
        regime_name = regime_info.get("regime", "UNKNOWN")
        adx = regime_info.get("wilder_adx_14", 0.0)

        if not is_fresh:
            q1_state = "FAIL"
            q1_status = "BLOCKED_STALE"
            q1_narrative = f"Market data is stale ({observed_age_h:.1f}h old > {max_age_hours:.1f}h limit). Live regime cannot be validated."
        elif regime_name in ["COMPRESSION", "VOLATILITY_COMPRESSION"] and adx < 15.0:
            q1_state = "PASS"
            q1_status = "WARNING_COMPRESSION"
            q1_narrative = f"Market is in severe compression (ADX {adx:.1f} < 15.0). Breakout directions are unpredictable; false breaks predominate. Regime conditionally evaluated."
        elif regime_name == "UNKNOWN":
            q1_state = "FAIL"
            q1_status = "FAIL_INVALID_REGIME"
            q1_narrative = "Regime classification failed or returned invalid."
        else:
            q1_state = "PASS"
            q1_status = "PASS"
            q1_narrative = f"Market is in {regime_name} (ADX {adx:.1f}, trend: {regime_info.get('trend_direction', 'NEUTRAL')}). Regime compatibility check passed."

        # ---------------------------------------------------------------------
        # Question 2: Directional Evidence
        # Semantics: Explicit INSUFFICIENT_EVIDENCE state.
        # Currently unauthorized pending new validated evidence under separate protocol.
        # ---------------------------------------------------------------------
        if not is_fresh:
            q2_state = "FAIL"
            q2_status = "BLOCKED_STALE"
            q2_narrative = "Directional evidence cannot be evaluated on stale market data."
        else:
            q2_state = "INSUFFICIENT_EVIDENCE"
            q2_status = "INSUFFICIENT_EVIDENCE"
            q2_narrative = (
                "Directional return classifiers achieve ~53.28% out-of-sample accuracy on hourly BTCUSD. "
                "Without external positioning shocks, empirical return edge is statistically indistinguishable "
                "from random drift (p >= 0.20). Directional prediction is currently unauthorized pending new "
                "validated evidence under a separately approved validation protocol. State is INSUFFICIENT_EVIDENCE "
                "(distinguished from technical failure)."
            )

        # ---------------------------------------------------------------------
        # Question 3: Entry Location (Structural Quality != Directional Alpha)
        # ---------------------------------------------------------------------
        cur_p = market_intel.get("last_observed_candle_price", live_price)
        bollinger_bounds = _validated_bollinger_bounds(regime_info)
        bb_lo, bb_mid, bb_up = bollinger_bounds if bollinger_bounds else (None, None, None)
        atr_usd = regime_info.get("atr_14_usd", 1200.0)

        if not is_fresh:
            q3_state = "FAIL"
            q3_status = "BLOCKED_STALE"
            q3_score = 0.0
            q3_quality = "UNAVAILABLE_STALE"
            q3_narrative = "Entry location cannot be confirmed on stale price history."
        elif bollinger_bounds is None:
            q3_state = "FAIL"
            q3_status = "BLOCKED_BOLLINGER_BOUNDS_UNAVAILABLE"
            q3_score = 0.0
            q3_quality = "UNAVAILABLE_BOLLINGER_BOUNDS"
            q3_narrative = "Entry location cannot be evaluated because valid Bollinger bounds are unavailable."
        else:
            dist_to_mid_pct = abs(cur_p - bb_mid) / cur_p * 100.0 if cur_p > 0 else 0.0
            dist_to_support_usd = cur_p - bb_lo
            dist_to_resistance_usd = bb_up - cur_p
            atr_multiple_to_sr = round(min(dist_to_support_usd, dist_to_resistance_usd) / atr_usd, 2) if atr_usd > 0 else 1.0

            if cur_p >= bb_up:
                q3_state = "FAIL"
                q3_status = "UNFAVOURABLE_OVERBOUGHT"
                q3_score = 30.0
                q3_quality = "EXTENDED_OVERBOUGHT"
                q3_narrative = (
                    f"Price (${cur_p:,.2f}) is extended at or above upper Bollinger Band (${bb_up:,.2f}). "
                    f"Location quality is poor due to adverse selection risk. Note: Location quality is not directional alpha."
                )
            elif cur_p <= bb_lo:
                q3_state = "FAIL"
                q3_status = "UNFAVOURABLE_OVERSOLD"
                q3_score = 30.0
                q3_quality = "EXTENDED_OVERSOLD"
                q3_narrative = (
                    f"Price (${cur_p:,.2f}) is depressed at or below lower Bollinger Band (${bb_lo:,.2f}). "
                    f"Location quality is poor due to mean-reversion snapback risk. Note: Location quality is not directional alpha."
                )
            else:
                q3_state = "PASS"
                q3_status = "ACCEPTABLE"
                q3_score = round(70.0 - (dist_to_mid_pct * 2.5), 1)
                q3_quality = "STRUCTURALLY_BALANCED"
                q3_narrative = (
                    f"Price (${cur_p:,.2f}) is within normal structural bands ({dist_to_mid_pct:.2f}% from 20h mean ${bb_mid:,.2f}). "
                    f"ATR distance: {atr_multiple_to_sr}x ATR to nearest structural boundary. "
                    f"Structural location passes technical checks; does NOT guarantee trade profitability."
                )

        # ---------------------------------------------------------------------
        # Question 4: Risk/Reward & Execution Economics
        # ---------------------------------------------------------------------
        atr_val = regime_info.get("atr_14_usd", 1200.0)
        tp_dist_pct = (atr_val * 2.0) / cur_p * 100.0 if cur_p > 0 else 2.0
        sl_dist_pct = (atr_val * 1.0) / cur_p * 100.0 if cur_p > 0 else 1.0
        drag_pct = drag_bps / 100.0
        p_be = (sl_dist_pct + drag_pct) / (tp_dist_pct + sl_dist_pct) if (tp_dist_pct + sl_dist_pct) > 0 else 0.50

        if not is_fresh:
            q4_state = "FAIL"
            q4_status = "BLOCKED_STALE"
            gross_ev_bps = 0.0
            net_ev_bps = 0.0
            q4_narrative = "Execution economics cannot be approved on stale candles."
        else:
            empirical_tp_rate = 0.335
            gross_ev_bps = round(((empirical_tp_rate * tp_dist_pct) - ((1.0 - empirical_tp_rate) * sl_dist_pct)) * 100.0, 2)
            net_ev_bps = round(gross_ev_bps - drag_bps, 2)

            if net_ev_bps <= 0:
                q4_state = "FAIL"
                q4_status = "FAILS_FEE_DRAG"
                q4_narrative = (
                    f"At {cost_venue} ({drag_bps:.1f} bps round-trip friction), required breakeven win rate is {p_be*100:.1f}%. "
                    f"Gross expected return is {gross_ev_bps:+.1f} bps. Total friction of {drag_bps:.1f} bps yields Net EV of "
                    f"{net_ev_bps:+.1f} bps/trade. Negative economics; fee drag consumes edge."
                )
            else:
                q4_state = "PASS"
                q4_status = "PASS"
                q4_narrative = f"Net EV is positive ({net_ev_bps:+.1f} bps) after {drag_bps:.1f} bps friction."

        # ---------------------------------------------------------------------
        # Question 5: Confidence & Calibration
        # N >= 30 is a diagnostic minimum only, NOT a statistical validation threshold.
        # ---------------------------------------------------------------------
        n_eff = None

        q5_state = "FAIL"
        q5_status = "CALIBRATION_UNAVAILABLE"
        q5_narrative = "No verifiable calibration artifact is configured; uncertainty coverage is unavailable."

        # ---------------------------------------------------------------------
        # Final Governed Decision
        # Invariant: Q1, Q3, Q4, Q5 CANNOT override Q2.
        # All 5 questions must strictly have state == "PASS" for ELIGIBLE.
        # ---------------------------------------------------------------------
        all_passed = (q1_state == "PASS" and q2_state == "PASS" and q3_state == "PASS" and q4_state == "PASS" and q5_state == "PASS")

        if not is_fresh:
            final_decision = "ABSTAIN"
            actionable_rec = "NO_TRADE"
            decision_reason = f"Trading blocked due to stale market data ({observed_age_h:.1f}h old > {max_age_hours:.1f}h limit). Market intelligence remains available as historical context."
        elif q2_state == "INSUFFICIENT_EVIDENCE":
            final_decision = "ABSTAIN"
            actionable_rec = "NO_TRADE"
            decision_reason = (
                "Trade authorization is ABSTAIN. Q2 Directional Evidence is INSUFFICIENT_EVIDENCE "
                "(currently unauthorized pending new validated evidence under a separately approved validation protocol). "
                "Individual checks Q1, Q3, Q4, Q5 cannot override directional evidence sufficiency."
            )
        elif not all_passed:
            final_decision = "ABSTAIN"
            actionable_rec = "NO_TRADE"
            failed_questions = []
            if q1_state != "PASS": failed_questions.append(f"Q1 Regime ({q1_status})")
            if q2_state != "PASS": failed_questions.append(f"Q2 Directional ({q2_status})")
            if q3_state != "PASS": failed_questions.append(f"Q3 Entry Location ({q3_status})")
            if q4_state != "PASS": failed_questions.append(f"Q4 Economics ({q4_status})")
            if q5_state != "PASS": failed_questions.append(f"Q5 Confidence ({q5_status})")
            decision_reason = f"Trade authorization failed {len(failed_questions)} gate(s): {', '.join(failed_questions)}."
        else:
            final_decision = "ELIGIBLE"
            actionable_rec = "SIMULATED_TRADE_ELIGIBLE"
            decision_reason = "All five independent trade gates satisfied."

        # User Intent Guardrail: Never let user bias override negative expectancy or insufficient evidence
        user_bias_rejected = False
        if user_intent_direction and user_intent_direction.upper() in ["LONG", "SHORT"] and final_decision != "ELIGIBLE":
            user_bias_rejected = True
            decision_reason += f" User preference '{user_intent_direction.upper()}' was evaluated and safely REJECTED by governance guardrails."

        return {
            "decision_timestamp_utc": eval_ts,
            "final_decision": final_decision,
            "actionable_recommendation": actionable_rec,
            "live_trading": "DISABLED — ANALYSIS ONLY",
            "decision_summary": decision_reason,
            "user_bias_rejected": user_bias_rejected,
            "execution_friction_assumed_bps": drag_bps,
            "cost_venue": cost_venue,
            "research_authorization_status": "OFFLINE_RESEARCH_ONLY",
            "directional_eligibility_lock": "CURRENTLY_UNAUTHORIZED_PENDING_NEW_VALIDATED_EVIDENCE",
            "five_question_evaluation": {
                "question_1_market_regime": {
                    "question": "Is BTC trending, ranging, compressing, or expanding?",
                    "state": q1_state,
                    "status": q1_status,
                    "passed": q1_state == "PASS",
                    "explanation": q1_narrative
                },
                "question_2_directional_evidence": {
                    "question": "Is there reliable evidence favouring LONG or SHORT?",
                    "state": q2_state,
                    "status": q2_status,
                    "passed": q2_state == "PASS",
                    "explanation": q2_narrative,
                    "research_authorization_state": "CURRENTLY_UNAUTHORIZED_PENDING_NEW_VALIDATED_EVIDENCE"
                },
                "question_3_entry_location": {
                    "question": "Is the proposed entry price favourable relative to current market structure?",
                    "state": q3_state,
                    "status": q3_status,
                    "passed": q3_state == "PASS",
                    "structural_location_quality": q3_quality,
                    "structural_location_score": q3_score,
                    "support_price": round(bb_lo, 2) if bb_lo is not None else None,
                    "resistance_price": round(bb_up, 2) if bb_up is not None else None,
                    "atr_14_distance_usd": round(atr_usd, 2),
                    "anti_conflation_notice": "Never equate location quality with probability of profit. A trade near support is not automatically a good LONG.",
                    "explanation": q3_narrative
                },
                "question_4_execution_economics": {
                    "question": "Is the potential return sufficient relative to adverse excursion and total costs?",
                    "state": q4_state,
                    "status": q4_status,
                    "passed": q4_state == "PASS",
                    "gross_expected_return_bps": gross_ev_bps,
                    "net_expected_value_bps": net_ev_bps,
                    "friction_breakdown": {
                        "venue": cost_venue,
                        "commission_round_trip_bps": round(drag_bps - 4.0, 1),
                        "spread_bps": 4.0,
                        "spread_status": "ESTIMATED_4BPS_UNAVAILABLE_WITHOUT_L2_DEPTH",
                        "slippage_bps": 0.0,
                        "slippage_status": "ESTIMATED_0BPS_MAKER_ASSUMED",
                        "total_round_trip_friction_bps": drag_bps,
                        "disclosure": "Figures are illustrative historical evaluation outputs; not predictive guarantees of actual future returns."
                    },
                    "explanation": q4_narrative
                },
                "question_5_confidence_calibration": {
                    "question": "How reliable is the underlying evidence in this particular market condition?",
                    "state": q5_state,
                    "status": q5_status,
                    "passed": q5_state == "PASS",
                    "diagnostic_sample_floor_n": 30,
                    "sample_size_classification": "DIAGNOSTIC_MINIMUM_ONLY — NOT_A_VALIDATION_THRESHOLD",
                    "sample_size_governance_notice": (
                        "N >= 30 is a descriptive engineering diagnostic floor, not proof of statistical evidence. "
                        "Effective sample size is unavailable without a dependence-aware estimate. "
                        "Confirmatory research claims require pre-registered protocol validation with N >= 100 clean prospective blocks."
                    ),
                    "effective_sample_size_estimate_n_eff": n_eff,
                    "calibration_status": "UNAVAILABLE",
                    "explanation": q5_narrative
                }
            }
        }

    def execute_decoupled_analysis(
        self,
        df_1h: Optional[pd.DataFrame],
        live_price: Optional[float] = None,
        enforce_freshness: bool = False,
        max_age_hours: float = 3.0,
        user_intent_direction: Optional[str] = None,
        cost_venue: str = "COINBASE_ADVANCED_87BPS",
        dataset_fingerprint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes complete decoupled analysis:
        1. Always generates Market Intelligence Report (even if stale or trading blocked).
        2. Strictly gates Trade Authorization based on the 5 Questions.
        """
        # Filter closed candles
        if df_1h is not None and not df_1h.empty:
            if "is_closed" in df_1h.columns:
                df_closed = df_1h[df_1h["is_closed"] == True].copy()
            else:
                df_closed = df_1h.copy()
        else:
            df_closed = None

        # Output A: Market Intelligence Report
        market_intel = self.compute_market_intelligence_report(
            df_closed=df_closed,
            live_price=live_price,
            max_age_hours=max_age_hours,
            dataset_fingerprint=dataset_fingerprint
        )

        ref_p = market_intel.get("last_observed_candle_price") or (live_price if live_price and live_price > 0 else 80000.0)

        # Output B: Trade Authorization (5 Questions)
        trade_auth = self.evaluate_five_question_trade_authorization(
            df_closed=df_closed,
            live_price=ref_p,
            market_intel=market_intel,
            user_intent_direction=user_intent_direction,
            cost_venue=cost_venue,
            max_age_hours=max_age_hours
        )

        return {
            "market_intelligence": market_intel,
            "trade_authorization": trade_auth,
            "is_read_only": True,
            "attempts_created": 0,
            "live_trading": "DISABLED — ANALYSIS ONLY"
        }


# Singleton engine instance
decoupled_analysis_engine = DecoupledAnalysisEngine()
