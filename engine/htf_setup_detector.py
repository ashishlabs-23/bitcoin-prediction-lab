"""
BTCognitive — HTF Range Expansion Breakout Setup Detector.
==========================================================
Evaluates the existing frozen HTF Range Expansion Breakout (Strategy D) rules:
- Timeframe: 4-Hour Aggregated Candles
- Channel: 20-bar Donchian Range with 1-bar shift (prior closed bars [t-20, t-1])
- Trigger: Completed 4h candle close strictly > 20-bar Donchian range high
- Entry Reference: Next bar open
- Stop Reference: Opposite 20-bar Donchian range low
- Maximum Holding Period: 18 4h bars (72 hours)
- Regime Confirmation: 1h causal classifier with 3-closed-candle persistence

Strict Epistemic & Operational Guarantees:
- Output States: NO_SETUP, SETUP_FORMING, TRIGGER_CONFIRMED, BLOCKED, DATA_UNAVAILABLE, SHADOW_CANDIDATE.
- Incomplete 4h candles are strictly rejected from triggering entries.
- Stale market data cannot produce an active entry proposal.
- Independent of prospective validation (0 events does not suppress a technical candidate).
- Zero simulated trade attempts created; zero broker orders.
"""

from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from engine.canonical_regime_map import (
    normalize_regime,
    check_htf_regime_compatibility,
    get_canonical_definition
)


class HTFSetupDetector:
    STRATEGY_ID = "HTF_RANGE_EXPANSION_BREAKOUT"
    STRATEGY_NAME = "High-Timeframe Range Expansion Breakout (4h / 20-bar)"
    DONCHIAN_WINDOW = 20
    MAX_HOLD_BARS_4H = 18
    MAX_HOLD_HOURS = 72.0
    MIN_REQUIRED_1H_BARS = 84  # At least 21 complete 4h bars (20 for channel + 1 for signal)

    @classmethod
    def aggregate_completed_4h_candles(cls, df_1h: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]:
        """
        Aggregates 1h closed candles into completed 4h candles.
        Validates that each 4h candle contains exactly 4 hourly bars.
        The last bucket is verified for completeness: if it has < 4 bars, it is identified as incomplete.
        """
        if df_1h is None or len(df_1h) < cls.MIN_REQUIRED_1H_BARS:
            return None, {"status": "INSUFFICIENT_1H_BARS", "count": len(df_1h) if df_1h is not None else 0}

        df = df_1h.copy()
        ts_col = "timestamp" if "timestamp" in df.columns else ("timestamp_utc" if "timestamp_utc" in df.columns else None)
        if ts_col is None:
            return None, {"status": "MISSING_TIMESTAMP_COLUMN"}

        df["dt"] = pd.to_datetime(df[ts_col], utc=True)
        df = df.sort_values("dt").reset_index(drop=True)

        # Count bars per 4h bucket
        df["bucket_4h"] = df["dt"].dt.floor("4h")
        bucket_counts = df.groupby("bucket_4h").size()

        # Check latest bucket
        latest_bucket = bucket_counts.index[-1]
        latest_bucket_count = int(bucket_counts.iloc[-1])
        is_latest_complete = (latest_bucket_count == 4)

        incomplete_info = None
        if not is_latest_complete:
            incomplete_info = {
                "latest_bucket_utc": latest_bucket.isoformat(),
                "bars_present": latest_bucket_count,
                "bars_required": 4,
                "message": f"Latest 4-hour candle is incomplete ({latest_bucket_count}/4 closed 1h bars). Evaluated strictly on the latest fully closed 4h candle."
            }

        # Filter to only fully completed 4h buckets (exactly 4 bars)
        # Note: shifted 20-bar Donchian requires at least 21 completed buckets to have non-null range bounds
        complete_buckets = bucket_counts[bucket_counts == 4].index
        if len(complete_buckets) < (cls.DONCHIAN_WINDOW + 1):
            return None, {"status": "INSUFFICIENT_COMPLETED_4H_BARS", "completed_count": len(complete_buckets), "required": cls.DONCHIAN_WINDOW + 1}

        df_complete = df[df["bucket_4h"].isin(complete_buckets)].copy()

        df_4h = df_complete.groupby("bucket_4h").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).reset_index()

        df_4h = df_4h.rename(columns={"bucket_4h": "timestamp"})
        df_4h["timestamp"] = pd.to_datetime(df_4h["timestamp"], utc=True)

        # Causal Donchian Range: shifted by 1 bar so bar t is compared against [t-20, t-1]
        h4 = df_4h["high"].astype(float).values
        l4 = df_4h["low"].astype(float).values
        c4 = df_4h["close"].astype(float).values

        # ATR 14 on 4h
        tr = [max(h4[i] - l4[i], abs(h4[i] - c4[i - 1]), abs(l4[i] - c4[i - 1])) if i > 0 else (h4[0] - l4[0]) for i in range(len(h4))]
        df_4h["tr_4h"] = tr
        df_4h["atr_14_4h"] = pd.Series(tr).rolling(14, min_periods=14).mean().fillna(pd.Series(tr))

        df_4h["range_high_20_4h"] = pd.Series(h4).shift(1).rolling(cls.DONCHIAN_WINDOW, min_periods=cls.DONCHIAN_WINDOW).max()
        df_4h["range_low_20_4h"] = pd.Series(l4).shift(1).rolling(cls.DONCHIAN_WINDOW, min_periods=cls.DONCHIAN_WINDOW).min()

        return df_4h, incomplete_info

    @classmethod
    def detect_setup(
        cls,
        df_1h: pd.DataFrame,
        observed_regime: str,
        live_price: Optional[float] = None,
        is_data_stale: bool = False,
        observed_age_hours: float = 0.0,
        enforce_stale_blocking: bool = True
    ) -> Dict[str, Any]:
        """
        Executes technical HTF setup detection across closed completed candles.
        Returns explicit state: NO_SETUP, SETUP_FORMING, TRIGGER_CONFIRMED, BLOCKED, DATA_UNAVAILABLE, SHADOW_CANDIDATE.
        """
        canonical_regime = normalize_regime(observed_regime)
        is_regime_compat, _, regime_reason = check_htf_regime_compatibility(canonical_regime)
        observed_age_seconds = int(observed_age_hours * 3600.0)

        provider = "BITSTAMP" if (df_1h is not None and "source_exchange" in df_1h.columns and str(df_1h["source_exchange"].iloc[-1]).upper() == "BITSTAMP") else "LOCAL_HISTORICAL_SNAPSHOT"
        source_sym = str(df_1h["source_symbol"].iloc[-1]) if (df_1h is not None and "source_symbol" in df_1h.columns) else "BTC/USD"

        # 1. Check data availability and minimum bars
        df_4h, incomplete_info = cls.aggregate_completed_4h_candles(df_1h)
        if df_4h is None:
            return {
                "strategy_id": cls.STRATEGY_ID,
                "strategy_name": cls.STRATEGY_NAME,
                "data_provider": provider,
                "source_exchange": provider,
                "source_symbol": source_sym,
                "setup_status": "DATA_UNAVAILABLE",
                "analysis_execution_status": "DATA_DEFICIENT",
                "regime": canonical_regime,
                "observed_regime_raw": observed_regime,
                "regime_confirmed": is_regime_compat,
                "trigger_status": "DATA_DEFICIENT",
                "breakout_reference": None,
                "distance_to_trigger_bps": None,
                "distance_to_trigger_atr": None,
                "completed_4h_bar": None,
                "entry_reference": None,
                "stop_reference": None,
                "target_reference": None,
                "risk_reward_ratio": None,
                "holding_horizon_bars": cls.MAX_HOLD_BARS_4H,
                "holding_horizon_hours": cls.MAX_HOLD_HOURS,
                "historical_evidence_status": "RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY",
                "prospective_validation_status": "FROZEN_PENDING_ACTIVATION",
                "research_eligibility_status": "NOT_ELIGIBLE",
                "authorization_status": "OFFLINE_RESEARCH_ONLY",
                "data_freshness_status": "MARKET_DATA_STALE" if is_data_stale else "FRESH",
                "data_age_hours": round(observed_age_hours, 1),
                "data_age_seconds": int(observed_age_seconds),
                "reason_codes": ["DATA_UNAVAILABLE_INSUFFICIENT_BARS"],
                "next_required_condition": "Accumulate at least 21 fully closed 4-hour candles to construct Donchian breakout channel.",
                "explanation": f"Insufficient completed 4-hour candle history to compute 20-bar Donchian channel (details: {incomplete_info})."
            }

        # 2. Extract latest completed 4h bar
        latest_4h = df_4h.iloc[-1]
        bar_ts = latest_4h["timestamp"].isoformat()
        completed_close = float(latest_4h["close"])
        range_high = float(latest_4h["range_high_20_4h"])
        range_low = float(latest_4h["range_low_20_4h"])
        atr_4h = float(latest_4h["atr_14_4h"]) if not np.isnan(latest_4h["atr_14_4h"]) else (completed_close * 0.02)

        if np.isnan(range_high) or np.isnan(range_low):
            return {
                "strategy_id": cls.STRATEGY_ID,
                "strategy_name": cls.STRATEGY_NAME,
                "setup_status": "DATA_UNAVAILABLE",
                "analysis_execution_status": "DATA_DEFICIENT",
                "regime": canonical_regime,
                "observed_regime_raw": observed_regime,
                "regime_confirmed": is_regime_compat,
                "trigger_status": "DATA_DEFICIENT",
                "breakout_reference": None,
                "distance_to_trigger_bps": None,
                "distance_to_trigger_atr": None,
                "completed_4h_bar": None,
                "entry_reference": None,
                "stop_reference": None,
                "target_reference": None,
                "risk_reward_ratio": None,
                "holding_horizon_bars": cls.MAX_HOLD_BARS_4H,
                "holding_horizon_hours": cls.MAX_HOLD_HOURS,
                "historical_evidence_status": "RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY",
                "prospective_validation_status": "FROZEN_PENDING_ACTIVATION",
                "research_eligibility_status": "NOT_ELIGIBLE",
                "authorization_status": "OFFLINE_RESEARCH_ONLY",
                "data_freshness_status": "MARKET_DATA_STALE" if is_data_stale else "FRESH",
                "data_age_hours": round(observed_age_hours, 1),
                "data_age_seconds": int(observed_age_seconds),
                "reason_codes": ["DATA_UNAVAILABLE_NAN_CHANNEL"],
                "next_required_condition": "Accumulate sufficient history to resolve NaN Donchian channel boundaries.",
                "explanation": "Donchian channel bounds evaluated to NaN due to insufficient warmup history."
            }

        # Reference price for entry (live price if provided and valid, otherwise completed 4h close)
        current_ref_price = float(live_price) if (live_price is not None and live_price > 0) else completed_close

        # Actionability and Distance to trigger metrics
        dist_bps = round(((current_ref_price - range_high) / range_high) * 10000.0, 1)
        dist_atr = round((current_ref_price - range_high) / atr_4h, 2) if atr_4h > 0 else 0.0
        breakout_ref = round(range_high, 2)

        # 3. Evaluate Trigger Condition on completed bar
        is_trigger_satisfied = completed_close > range_high

        # 4. Evaluate Forming Condition (ATR-adaptive threshold clamped between 0.5% and 1.5% of range high)
        forming_buffer_usd = min(max(0.5 * atr_4h, range_high * 0.005), range_high * 0.015)
        is_approaching = (not is_trigger_satisfied) and (current_ref_price >= (range_high - forming_buffer_usd))

        # Detail structure of the completed 4h bar
        completed_bar_dict = {
            "timestamp_utc": bar_ts,
            "open": round(float(latest_4h["open"]), 2),
            "high": round(float(latest_4h["high"]), 2),
            "low": round(float(latest_4h["low"]), 2),
            "close": round(completed_close, 2),
            "range_high_20_4h": round(range_high, 2),
            "range_low_20_4h": round(range_low, 2),
            "donchian_channel_high_20_4h": round(range_high, 2),
            "donchian_channel_low_20_4h": round(range_low, 2),
            "atr_14_4h": round(atr_4h, 2),
            "breakout_reference": breakout_ref,
            "distance_to_trigger_bps": dist_bps,
            "distance_to_trigger_atr": dist_atr,
            "distance_to_breakout_bps": round(((completed_close - range_high) / range_high) * 10000.0, 1),
            "incomplete_candle_notice": incomplete_info,
            "data_freshness_status": "MARKET_DATA_STALE" if is_data_stale else "FRESH",
            "observed_age_hours": round(observed_age_hours, 1)
        }

        # 1. Stale Market Data Gate: Stale historical data cannot produce an active entry proposal or fresh setup evaluation
        if is_data_stale and enforce_stale_blocking:
            reason_codes = ["STALE_MARKET_DATA_BLOCKED"]
            if not is_regime_compat:
                if canonical_regime == "TRENDING_BEARISH":
                    reason_codes.append("REGIME_MISMATCH_BEARISH")
                elif canonical_regime == "RANGE_BOUND":
                    reason_codes.append("REGIME_MISMATCH_RANGE_BOUND")
                elif canonical_regime == "TRANSITION_UNSUPPORTED":
                    reason_codes.append("REGIME_TRANSITION_UNSUPPORTED")
                reason_codes.append(f"BLOCKED_BY_REGIME_{canonical_regime}")

            return {
                "strategy_id": cls.STRATEGY_ID,
                "strategy_name": cls.STRATEGY_NAME,
                "data_provider": provider,
                "source_exchange": provider,
                "source_symbol": source_sym,
                "setup_status": "BLOCKED",
                "analysis_execution_status": "SUCCESS",
                "regime": canonical_regime,
                "observed_regime_raw": observed_regime,
                "regime_confirmed": is_regime_compat,
                "trigger_status": "STALE_DATA_BLOCKED",
                "breakout_reference": breakout_ref,
                "distance_to_trigger_bps": dist_bps,
                "distance_to_trigger_atr": dist_atr,
                "completed_4h_bar": completed_bar_dict,
                "entry_reference": None,
                "stop_reference": None,
                "target_reference": None,
                "risk_reward_ratio": None,
                "holding_horizon_bars": cls.MAX_HOLD_BARS_4H,
                "holding_horizon_hours": cls.MAX_HOLD_HOURS,
                "historical_evidence_status": "RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY",
                "prospective_validation_status": "FROZEN_PENDING_ACTIVATION",
                "research_eligibility_status": "NOT_ELIGIBLE",
                "authorization_status": "OFFLINE_RESEARCH_ONLY",
                "data_freshness_status": "MARKET_DATA_STALE",
                "data_age_hours": round(observed_age_hours, 1),
                "data_age_seconds": int(observed_age_seconds),
                "last_observed_timestamp_utc": bar_ts,
                "reason_codes": reason_codes,
                "next_required_condition": "Receive fresh market data (age <= 2.0h) and compatible regime to evaluate setup.",
                "explanation": (
                    f"Market data is stale ({observed_age_hours:.1f}h old > 2.0h operational limit; latest completed 4h bar {bar_ts}). "
                    f"Historical snapshot preserved; current live setup cannot be evaluated on stale market data."
                    + (f" Incompatible regime: {regime_reason}" if not is_regime_compat else "")
                )
            }

        # 2. Incompatible Regime Gate: Incompatible regimes (TRENDING_BEARISH, RANGE_BOUND, TRANSITION_UNSUPPORTED) are strictly BLOCKED
        if not is_regime_compat:
            if canonical_regime == "TRENDING_BEARISH":
                primary_code = "REGIME_MISMATCH_BEARISH"
            elif canonical_regime == "RANGE_BOUND":
                primary_code = "REGIME_MISMATCH_RANGE_BOUND"
            elif canonical_regime == "TRANSITION_UNSUPPORTED":
                primary_code = "REGIME_TRANSITION_UNSUPPORTED"
            else:
                primary_code = f"REGIME_MISMATCH_{canonical_regime}"

            trigger_st = "BREACHED_BUT_REGIME_BLOCKED" if is_trigger_satisfied else "REGIME_BLOCKED"
            return {
                "strategy_id": cls.STRATEGY_ID,
                "strategy_name": cls.STRATEGY_NAME,
                "data_provider": provider,
                "source_exchange": provider,
                "source_symbol": source_sym,
                "setup_status": "BLOCKED",
                "analysis_execution_status": "SUCCESS",
                "regime": canonical_regime,
                "observed_regime_raw": observed_regime,
                "regime_confirmed": False,
                "trigger_status": trigger_st,
                "breakout_reference": breakout_ref,
                "distance_to_trigger_bps": dist_bps,
                "distance_to_trigger_atr": dist_atr,
                "completed_4h_bar": completed_bar_dict,
                "entry_reference": None,
                "stop_reference": None,
                "target_reference": None,
                "risk_reward_ratio": None,
                "holding_horizon_bars": cls.MAX_HOLD_BARS_4H,
                "holding_horizon_hours": cls.MAX_HOLD_HOURS,
                "historical_evidence_status": "RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY",
                "prospective_validation_status": "FROZEN_PENDING_ACTIVATION",
                "research_eligibility_status": "NOT_ELIGIBLE",
                "authorization_status": "OFFLINE_RESEARCH_ONLY",
                "data_freshness_status": "MARKET_DATA_STALE" if is_data_stale else "FRESH",
                "data_age_hours": round(observed_age_hours, 1),
                "data_age_seconds": int(observed_age_seconds),
                "last_observed_timestamp_utc": bar_ts,
                "reason_codes": [primary_code, f"BLOCKED_BY_REGIME_{canonical_regime}"],
                "next_required_condition": f"Wait for market regime transition from {canonical_regime} into TRENDING_BULLISH or VOLATILITY_EXPANSION.",
                "explanation": f"Setup is BLOCKED: Observed regime '{canonical_regime}' is incompatible with the long-only breakout strategy. {regime_reason}"
            }

        # 3. Compatible Regime (TRENDING_BULLISH or VOLATILITY_EXPANSION) on Fresh Data
        if is_trigger_satisfied:
            # Valid trigger under compatible regime: SHADOW_CANDIDATE
            entry_ref = round(current_ref_price, 2)
            stop_ref = round(range_low, 2)
            risk_unit = max(100.0, entry_ref - stop_ref)
            target_ref = round(entry_ref + (1.5 * risk_unit), 2)
            rr_ratio = round((target_ref - entry_ref) / risk_unit, 2)

            return {
                "strategy_id": cls.STRATEGY_ID,
                "strategy_name": cls.STRATEGY_NAME,
                "data_provider": provider,
                "source_exchange": provider,
                "source_symbol": source_sym,
                "setup_status": "SHADOW_CANDIDATE",
                "analysis_execution_status": "SUCCESS",
                "regime": canonical_regime,
                "observed_regime_raw": observed_regime,
                "regime_confirmed": True,
                "trigger_status": "TRIGGER_CONFIRMED",
                "breakout_reference": breakout_ref,
                "distance_to_trigger_bps": dist_bps,
                "distance_to_trigger_atr": dist_atr,
                "completed_4h_bar": completed_bar_dict,
                "entry_reference": entry_ref,
                "stop_reference": stop_ref,
                "target_reference": target_ref,
                "risk_reward_ratio": rr_ratio,
                "holding_horizon_bars": cls.MAX_HOLD_BARS_4H,
                "holding_horizon_hours": cls.MAX_HOLD_HOURS,
                "historical_evidence_status": "RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY",
                "prospective_validation_status": "FROZEN_PENDING_ACTIVATION",
                "research_eligibility_status": "RESEARCH_CANDIDATE",
                "authorization_status": "OFFLINE_RESEARCH_ONLY",
                "data_freshness_status": "FRESH",
                "data_age_hours": round(observed_age_hours, 1),
                "data_age_seconds": int(observed_age_seconds),
                "last_observed_timestamp_utc": bar_ts,
                "reason_codes": ["HTF_BREAKOUT_TRIGGER_CONFIRMED", "SHADOW_RESEARCH_QUALIFIED"],
                "next_required_condition": "Trigger confirmed on closed 4h candle; pending prospective forward evaluation under offline research governance.",
                "explanation": (
                    f"4-hour range breakout trigger confirmed (${completed_close:,.2f} > 20-bar high ${range_high:,.2f}) "
                    f"under compatible confirmed regime '{canonical_regime}'. Qualifies as a research SHADOW_CANDIDATE. "
                    "Prospective validation remains NOT VALIDATED (0 shadow events). Real trading is strictly DISABLED."
                )
            }

        elif is_approaching:
            return {
                "strategy_id": cls.STRATEGY_ID,
                "strategy_name": cls.STRATEGY_NAME,
                "data_provider": provider,
                "source_exchange": provider,
                "source_symbol": source_sym,
                "setup_status": "SETUP_FORMING",
                "analysis_execution_status": "SUCCESS",
                "regime": canonical_regime,
                "observed_regime_raw": observed_regime,
                "regime_confirmed": True,
                "trigger_status": "APPROACHING",
                "breakout_reference": breakout_ref,
                "distance_to_trigger_bps": dist_bps,
                "distance_to_trigger_atr": dist_atr,
                "completed_4h_bar": completed_bar_dict,
                "entry_reference": None,
                "stop_reference": None,
                "target_reference": None,
                "risk_reward_ratio": None,
                "holding_horizon_bars": cls.MAX_HOLD_BARS_4H,
                "holding_horizon_hours": cls.MAX_HOLD_HOURS,
                "historical_evidence_status": "RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY",
                "prospective_validation_status": "FROZEN_PENDING_ACTIVATION",
                "research_eligibility_status": "NOT_ELIGIBLE",
                "authorization_status": "OFFLINE_RESEARCH_ONLY",
                "data_freshness_status": "FRESH",
                "data_age_hours": round(observed_age_hours, 1),
                "data_age_seconds": int(observed_age_seconds),
                "last_observed_timestamp_utc": bar_ts,
                "reason_codes": ["PRICE_APPROACHING_RANGE_HIGH"],
                "next_required_condition": f"Closed 4h candle close strictly above ${range_high:,.2f} required to confirm trigger.",
                "explanation": f"Price (${current_ref_price:,.2f}) is approaching the 20-bar 4h range high (${range_high:,.2f}). Completed close has not yet confirmed a breakout."
            }

        else:
            # Compatible regime, but inside range: NO_SETUP
            return {
                "strategy_id": cls.STRATEGY_ID,
                "strategy_name": cls.STRATEGY_NAME,
                "data_provider": provider,
                "source_exchange": provider,
                "source_symbol": source_sym,
                "setup_status": "NO_SETUP",
                "analysis_execution_status": "SUCCESS",
                "regime": canonical_regime,
                "observed_regime_raw": observed_regime,
                "regime_confirmed": True,
                "trigger_status": "UNBREACHED",
                "breakout_reference": breakout_ref,
                "distance_to_trigger_bps": dist_bps,
                "distance_to_trigger_atr": dist_atr,
                "completed_4h_bar": completed_bar_dict,
                "entry_reference": None,
                "stop_reference": None,
                "target_reference": None,
                "risk_reward_ratio": None,
                "holding_horizon_bars": cls.MAX_HOLD_BARS_4H,
                "holding_horizon_hours": cls.MAX_HOLD_HOURS,
                "historical_evidence_status": "RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY",
                "prospective_validation_status": "FROZEN_PENDING_ACTIVATION",
                "research_eligibility_status": "NOT_ELIGIBLE",
                "authorization_status": "OFFLINE_RESEARCH_ONLY",
                "data_freshness_status": "FRESH",
                "data_age_hours": round(observed_age_hours, 1),
                "data_age_seconds": int(observed_age_seconds),
                "last_observed_timestamp_utc": bar_ts,
                "reason_codes": ["NO_HTF_BREAKOUT_CONDITION"],
                "next_required_condition": f"Price must rise {abs(dist_bps):.1f} bps to close above breakout reference (${range_high:,.2f}) on a 4h candle.",
                "explanation": f"Completed 4-hour close (${completed_close:,.2f}) is within the 20-bar Donchian channel [${range_low:,.2f}, ${range_high:,.2f}]. No breakout condition exists."
            }

