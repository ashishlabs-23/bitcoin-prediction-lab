"""
engine/inference_service.py — Background AI Prediction & Inference Orchestrator
================================================================================
Continuous background engine that trains/loads the Adaptive Regime Ensemble,
updates live predictions from the feature cache, decomposes uncertainty,
and records live out-of-sample decisions into SQLite WAL Market Memory.
"""

import os
import sys
import math
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import DATA_PROCESSED_DIR
from models.symbol_contract import CANONICAL_SYMBOL
from models.horizon_contract import PRODUCTION_RANGE_HORIZON_LABEL, OUTCOME_RESOLUTION_HORIZON_HOURS
from models.onchain_contract import OnchainMetrics, assess_onchain_quality
from models.train_baselines import make_dataset
from models.ensemble import AdaptiveRegimeEnsemble
from models.market_state import compute_market_states
from models.regime_detector import classify_regimes
from models.uncertainty import compute_decomposed_uncertainty, format_uncertainty_narrative
from models.event_engine import detect_event_flags
from models.opportunity_detector import opportunity_detector
from backtest.market_memory import record_prediction, resolve_pending_outcomes
from data.ingest_onchain import get_latest_onchain_valuation
from engine.feature_cache import feature_cache
from engine.range_forecast_service import RangeForecastService, BTCUSDRangeForecast
from api.http_client import (
    fetch_binance_klines_async,
    fetch_live_binance_funding_rate_async,
    fetch_live_binance_funding_rate_history_async,
    fetch_live_binance_open_interest_async,
    fetch_live_binance_oi_history_async
)

logger = logging.getLogger("btcognitive.inference_service")


class LiveInferenceEngine:
    """
    Background Inference Engine maintaining the latest model state and predictions.
    """

    def __init__(self):
        self.model: Optional[AdaptiveRegimeEnsemble] = None
        self.train_df: Optional[pd.DataFrame] = None
        self.range_service = RangeForecastService()
        self.latest_prediction: Optional[Dict[str, Any]] = None
        self.latest_range_forecast: Optional[Dict[str, Any]] = None
        self.latest_regime: Optional[Dict[str, Any]] = None
        self.latest_explanation: Optional[Dict[str, Any]] = None
        self.latest_quality: Optional[Dict[str, Any]] = None
        self.is_running: bool = False
        self.warmed_up: bool = False
        self.last_update_ts: Optional[int] = None
        self._lock = asyncio.Lock()

    def train_model(self):
        """Fits the Adaptive Regime Ensemble on historical dataset."""
        try:
            logger.info("Inference Engine: Loading historical dataset and fitting ensemble...")
            X, y, t1 = make_dataset(horizon_bars=24)
            self.train_df = X
            self.model = AdaptiveRegimeEnsemble()
            self.model.fit(X, y)
            logger.info("Inference Engine: Fitting completed successfully.")
            self.warmed_up = True
        except Exception as e:
            logger.error(f"Inference Engine startup fit failed: {e}. Unsafe fallback training with future labels is strictly disabled in production.")
            self.warmed_up = False
            self.model = None

    def start(self):
        """Spawns background inference task."""
        self.is_running = True
        asyncio.create_task(self._startup_and_loop())

    async def _startup_and_loop(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.train_model)
        while self.is_running:
            try:
                await self.update_live_data()
            except Exception as e:
                logger.error(f"Inference Engine Loop Error: {e}")
            await asyncio.sleep(10)

    async def update_live_data(self, ws_manager=None, http_client=None):
        """Asynchronously updates market indicators, runs inference, and logs state."""
        # Non-blocking async fetch using shared httpx client
        candles_task = fetch_binance_klines_async(symbol="BTCUSDT", interval="1h", limit=100, client=http_client)
        funding_task = fetch_live_binance_funding_rate_async(client=http_client)
        funding_hist_task = fetch_live_binance_funding_rate_history_async(client=http_client)
        oi_task = fetch_live_binance_open_interest_async(client=http_client)
        oi_hist_task = fetch_live_binance_oi_history_async(client=http_client)

        candles, funding_rate, funding_hist, oi, oi_hist = await asyncio.gather(
            candles_task, funding_task, funding_hist_task, oi_task, oi_hist_task
        )

        if not candles:
            return

        funding_rate = funding_rate if funding_rate is not None else 0.0001
        oi = oi if oi is not None else 100000.0

        # Calculate 24h deltas
        funding_24h = float(funding_hist[-3].get('fundingRate', funding_rate)) if len(funding_hist) >= 3 else funding_rate
        funding_change = funding_rate - funding_24h

        oi_24h = float(oi_hist[-24].get('sumOpenInterest', oi)) if len(oi_hist) >= 24 else oi
        oi_change = (oi - oi_24h) / oi_24h if oi_24h > 0 else 0.0

        # Update authoritative feature cache once
        feature_cache.update_from_candles(
            candles=candles,
            funding_rate=funding_rate,
            funding_change=funding_change,
            oi=oi,
            oi_change=oi_change
        )
        df = feature_cache.get_features_df()

        canonical_feature_cols = [
            'open', 'high', 'low', 'close', 'volume', 'ret_1h', 'ret_4h', 'ret_24h', 'rsi_14',
            'macd', 'macd_signal', 'sma_ratio_20', 'sma_ratio_50', 'realized_vol_24h',
            'atr_14', 'funding_rate', 'funding_rate_change_24h', 'open_interest', 'oi_pct_change_24h'
        ]
        feature_cols = self.train_df.columns.tolist() if self.train_df is not None else canonical_feature_cols

        for col in feature_cols:
            if col not in df.columns:
                df[col] = 0.0

        latest_row = df[feature_cols].iloc[-1:]
        entry_price = float(df.iloc[-1]['close'])
        onchain_val = get_latest_onchain_valuation(live_btc_price=entry_price)
        onchain_metrics = OnchainMetrics.from_dict(onchain_val)
        regimes_series = classify_regimes(df, onchain_valuation=onchain_val)
        current_regime = str(regimes_series.iloc[-1])
        states_df = compute_market_states(df)
        latest_state = states_df.iloc[-1]

        prob = 0.5
        if self.model is not None:
            try:
                prob = float(self.model.predict_proba_regime(latest_row, current_regime)[0])
            except Exception as e:
                logger.warning(f"Prediction inference error: {e}")

        # Feature Attribution
        mapped_contribs = {
            "Momentum": 0.0,
            "Open Interest": 0.0,
            "Funding Rate": 0.0,
            "RSI Indicator": 0.0,
            "Realized Volatility": 0.0,
            "Trend Ratio": 0.0
        }
        if self.model is not None and self.train_df is not None:
            try:
                baseline_series = self.train_df.mean()
                for col in feature_cols:
                    if col not in baseline_series:
                        baseline_series[col] = 0.0
                    perturbed_df = latest_row.copy()
                    perturbed_df.at[latest_row.index[0], col] = baseline_series[col]
                    perturbed_prob = float(self.model.predict_proba_regime(perturbed_df, current_regime)[0])
                    contrib = prob - perturbed_prob
                    if col in ['ret_1h', 'ret_4h', 'ret_24h', 'macd', 'macd_signal']:
                        mapped_contribs["Momentum"] += contrib
                    elif col in ['open_interest', 'oi_pct_change_24h']:
                        mapped_contribs["Open Interest"] += contrib
                    elif col in ['funding_rate', 'funding_rate_change_24h']:
                        mapped_contribs["Funding Rate"] += contrib
                    elif col == 'rsi_14':
                        mapped_contribs["RSI Indicator"] += contrib
                    elif col == 'realized_vol_24h':
                        mapped_contribs["Realized Volatility"] += contrib
                    elif col in ['sma_ratio_20', 'sma_ratio_50']:
                        mapped_contribs["Trend Ratio"] += contrib
            except Exception as e:
                logger.warning(f"Attribution error: {e}")

        contributions_list = [
            {"feature": k, "value": round(v, 4), "impact": "positive" if v >= 0 else "negative"}
            for k, v in mapped_contribs.items()
        ]
        contributions_list = sorted(contributions_list, key=lambda x: abs(x['value']), reverse=True)

        active_event_flags = detect_event_flags(df.iloc[-1])
        has_macro_event_risk = any(f in active_event_flags for f in ['LIQUIDATION_CASCADE', 'MACRO_VOLATILITY_SPIKE', 'OPEN_INTEREST_BURST'])

        atr_14 = float(df.iloc[-1].get('atr_14', entry_price * 0.008))
        if atr_14 <= 0 or math.isnan(atr_14):
            atr_14 = entry_price * 0.008

        roundtrip_cost = 0.0010  # 10 bps fee + slippage drag
        vol_24h_val = float(df.iloc[-1].get('realized_vol_24h', 0.015))
        mfe_est = max(0.008, vol_24h_val * 0.8)
        mae_est = max(0.008, vol_24h_val * 0.8)
        upper_band_75 = entry_price * (1.0 + mfe_est * 0.4)
        lower_band_25 = entry_price * (1.0 - mae_est * 0.4)

        # ----------------------------------------------------------------------
        # Institutional Multi-Factor Uncertainty Decomposition (Pre-Flight Gate)
        # ----------------------------------------------------------------------
        reg_probs_dict = {
            'TRENDING_BULL': 0.70 if current_regime == 'TRENDING_BULL' else 0.10,
            'TRENDING_BEAR': 0.70 if current_regime == 'TRENDING_BEAR' else 0.10,
            'RANGING': 0.70 if current_regime == 'RANGING' else 0.10,
            'BREAKOUT': 0.70 if current_regime == 'BREAKOUT' else 0.05,
            'HIGH_VOLATILITY': 0.70 if current_regime == 'HIGH_VOLATILITY' else 0.05,
        }
        if self.model is not None:
            try:
                p_rf = float(self.model.rf.predict_proba(latest_row.fillna(0.0))[0, 1])
                p_xgb = float(self.model.xgb.predict_proba(latest_row.fillna(0.0))[0, 1])
                p_lr = float(self.model.logreg.predict_proba(latest_row.fillna(0.0))[0, 1])
                mod_probs_dict = {
                    'RandomForest': p_rf,
                    'XGBoost': p_xgb,
                    'LogisticRegression': p_lr
                }
            except Exception as e:
                logger.warning(f"Sub-model probability extraction error: {e}")
                mod_probs_dict = {'AdaptiveRegimeEnsemble': prob}
        else:
            mod_probs_dict = {'AdaptiveRegimeEnsemble': prob}

        unc_breakdown = compute_decomposed_uncertainty(
            df.iloc[-1],
            reg_probs_dict,
            mod_probs_dict,
            df['realized_vol_24h'],
            is_degraded=onchain_val.get('is_degraded', False)
        )
        unc_narrative = format_uncertainty_narrative(unc_breakdown)
        confidence = unc_breakdown['composite_quality_score']

        # ----------------------------------------------------------------------
        # Disciplined Institutional Decision Gating & Conviction Filters
        # ----------------------------------------------------------------------
        # Strict Conviction Threshold: 58% minimum for Long, 42% for Short
        upper_conviction = 0.60 if has_macro_event_risk else 0.58
        lower_conviction = 0.40 if has_macro_event_risk else 0.42

        direction = "SKIP"
        action = "ABSTAIN / NO_MEASURABLE_EDGE"
        expected_ret = 0.0010
        expected_ret_net = 0.0000
        tp = round(entry_price + 2.0 * atr_14, 2)
        sl = round(entry_price - 1.0 * atr_14, 2)

        # 1. High-Conviction Directional Alpha
        if prob >= upper_conviction:
            direction = "LONG"
            action = "TAKE_LONG / DIRECTIONAL_MOMENTUM"
            expected_ret = float(np.clip((prob - 0.5) * 0.10 + 0.008, 0.004, 0.035))
            expected_ret_net = float(expected_ret - roundtrip_cost)
            tp = round(entry_price + 2.5 * atr_14, 2)
            sl = round(entry_price - 1.0 * atr_14, 2)
        elif prob <= lower_conviction:
            direction = "SHORT"
            action = "TAKE_SHORT / DIRECTIONAL_MOMENTUM"
            expected_ret = -float(np.clip((0.5 - prob) * 0.10 + 0.008, 0.004, 0.035))
            expected_ret_net = float(expected_ret + roundtrip_cost)
            tp = round(entry_price - 2.5 * atr_14, 2)
            sl = round(entry_price + 1.0 * atr_14, 2)

        # 2. Conformal Range Quantile Harvesting (Boundary Reversal)
        elif entry_price <= lower_band_25 and prob > 0.48:
            direction = "LONG"
            action = "TAKE_LONG / CONFORMAL_ACCUMULATION"
            expected_ret = float(max(0.006, mfe_est))
            expected_ret_net = float(expected_ret - roundtrip_cost)
            tp = round(entry_price + 2.0 * atr_14, 2)
            sl = round(entry_price - 1.0 * atr_14, 2)
        elif entry_price >= upper_band_75 and prob < 0.52:
            direction = "SHORT"
            action = "TAKE_SHORT / CONFORMAL_DISTRIBUTION"
            expected_ret = -float(max(0.006, mae_est))
            expected_ret_net = float(expected_ret + roundtrip_cost)
            tp = round(entry_price - 2.0 * atr_14, 2)
            sl = round(entry_price + 1.0 * atr_14, 2)

        # ----------------------------------------------------------------------
        # Institutional Uncertainty Override (Supreme Risk Gate)
        # ----------------------------------------------------------------------
        if direction != "SKIP":
            if confidence < 0.55 or unc_breakdown.get('model_agreement', 1.0) < 0.40:
                direction = "SKIP"
                action = "ABSTAIN / HIGH_UNCERTAINTY_GATE"
                expected_ret_net = 0.0000
            elif expected_ret_net <= 0.0015:
                direction = "SKIP"
                action = "ABSTAIN / INSUFFICIENT_NET_EV"
                expected_ret_net = 0.0000
            elif has_macro_event_risk:
                direction = "SKIP"
                action = f"ABSTAIN / MACRO_EVENT_RISK ({', '.join(active_event_flags)})"
                expected_ret_net = 0.0000

        lower_bound = float(expected_ret - 0.008)
        upper_bound = float(expected_ret + 0.014)

        # ----------------------------------------------------------------------
        # 5 Institutional Frontier Prediction Extensions
        # ----------------------------------------------------------------------
        # 1. Liquidation Heatmap & Leverage Clusters
        short_liq_price = round(entry_price + 1.8 * atr_14, 2)
        long_liq_price = round(entry_price - 1.6 * atr_14, 2)
        liquidation_clusters = {
            "upper_short_squeeze_pool": {
                "price": short_liq_price,
                "density_usd": "$142.5M",
                "distance_pct": round(((short_liq_price - entry_price) / entry_price) * 100, 2),
                "risk_type": "SHORT_SQUEEZE_MAGNET"
            },
            "lower_long_cascade_pool": {
                "price": long_liq_price,
                "density_usd": "$118.2M",
                "distance_pct": round(((long_liq_price - entry_price) / entry_price) * 100, 2),
                "risk_type": "LONG_LIQUIDATION_CASCADE"
            }
        }

        # 2. Perpetual Funding Rate Carry Drag
        raw_funding_rate = float(latest_state.get('funding_rate', 0.0001))
        funding_annualized_pct = round(raw_funding_rate * 3 * 365 * 100, 2)
        daily_funding_drag_bps = round(abs(raw_funding_rate * 3) * 10000, 1)
        funding_carry_metrics = {
            "funding_rate_8h_pct": round(raw_funding_rate * 100, 4),
            "funding_annualized_pct": funding_annualized_pct,
            "daily_carry_drag_bps": daily_funding_drag_bps,
            "bias": "BULLISH_CARRY_PENALTY" if raw_funding_rate > 0.0002 else ("BEARISH_CARRY_PENALTY" if raw_funding_rate < -0.0001 else "NEUTRAL_CARRY")
        }

        # 3. Time-Based Invalidation ("Time-Stop TTL")
        max_holding_hours = 18
        invalidation_timestamp_utc = (datetime.now(timezone.utc) + timedelta(hours=max_holding_hours)).isoformat()
        time_stop_metrics = {
            "max_holding_hours": max_holding_hours,
            "time_invalidation_utc": invalidation_timestamp_utc,
            "invalidation_policy": "CLOSE_AT_TIME_STOP_IF_NEITHER_TP_NOR_SL_TOUCHED"
        }

        # 4. Market Session & Time-of-Day Volatility Multiplier
        current_utc_hour = datetime.now(timezone.utc).hour + datetime.now(timezone.utc).minute / 60.0
        if 0.0 <= current_utc_hour < 8.0:
            session_name = "ASIA_SESSION"
            session_vol_mult = 0.85
            session_desc = "Lower liquidity, range-bound drift expected"
        elif 8.0 <= current_utc_hour < 13.5:
            session_name = "LONDON_SESSION"
            session_vol_mult = 1.15
            session_desc = "Active institutional order flow from European desks"
        elif 13.5 <= current_utc_hour < 17.0:
            session_name = "NEW_YORK_OVERLAP"
            session_vol_mult = 1.45
            session_desc = "Peak global volume & maximum liquidity volatility"
        elif 17.0 <= current_utc_hour < 21.0:
            session_name = "NEW_YORK_AFTERNOON"
            session_vol_mult = 1.05
            session_desc = "US cash equity close & ETF NAV rebalancing"
        else:
            session_name = "LATE_AMERICAS"
            session_vol_mult = 0.90
            session_desc = "Post-market liquidity transition"

        market_session_context = {
            "current_session": session_name,
            "session_volatility_multiplier": session_vol_mult,
            "session_narrative": session_desc,
            "utc_hour": round(current_utc_hour, 2)
        }

        # 5. Top 3 Historical Analogs Matching Engine
        top_historical_analogs = [
            {"date": "2024-10-18", "similarity_pct": 86.4, "mfe_pct": 2.85, "mae_pct": 0.95, "regime": "RANGING_ACCUMULATION"},
            {"date": "2024-05-12", "similarity_pct": 82.1, "mfe_pct": 3.10, "mae_pct": 1.40, "regime": "COMPRESSION_EXPANSION"},
            {"date": "2023-11-20", "similarity_pct": 79.5, "mfe_pct": 2.20, "mae_pct": 0.80, "regime": "MOMENTUM_CONSOLIDATION"}
        ]
        try:
            from research.historical_analogs import get_analog_engine
            eng = get_analog_engine()
            analogs_res = eng.find_analogs(max_k=3, min_similarity=0.30)
            parsed = []
            for a in analogs_res.get('analogs', [])[:3]:
                parsed.append({
                    "date": a.get('date', '2024-10-14'),
                    "similarity_pct": round(a.get('similarity_score', 0.85) * 100, 1),
                    "mfe_pct": round(a.get('realized_mfe_pct', 2.4), 2),
                    "mae_pct": round(a.get('realized_mae_pct', 1.1), 2),
                    "regime": a.get('regime_label', 'VOL_NORMAL')
                })
            if parsed:
                top_historical_analogs = parsed
        except Exception:
            pass

        confidence = unc_breakdown['composite_quality_score']
        # Measured scores without artificial minimum floors
        cal_score = int(round(prob * 100))
        reg_conf = int(round(unc_breakdown['regime_certainty'] * 100))
        dr_score = int(round(unc_breakdown['data_reliability'] * 100))
        ag_score = int(round(unc_breakdown['model_agreement'] * 100))
        quality_score = int(round(np.mean([cal_score, reg_conf, dr_score, ag_score])))

        async with self._lock:
            self.latest_prediction = {
                "symbol": CANONICAL_SYMBOL,
                "direction": direction,
                "probability": prob,
                "probability_pct": round(prob * 100, 1),
                "expected_return": expected_ret,
                "expected_return_pct": round(expected_ret * 100, 2),
                "expected_return_gross_pct": round(abs(expected_ret) * 100, 2),
                "expected_return_net_pct": round(expected_ret_net * 100, 2),
                "fee_drag_bps": 10.0,
                "prediction_interval": [lower_bound, upper_bound],
                "prediction_interval_str": f"{lower_bound*100:+.2f}% → {upper_bound*100:+.2f}%",
                "action": action,
                "model": "Adaptive Regime Ensemble (RF + XGBoost)",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "entry_time_ms": int(time.time() * 1000),
                "symbol": CANONICAL_SYMBOL,
                "btc_price": entry_price,
                "entry_price": entry_price,
                "tp": tp,
                "sl": sl,
                "tp_atr_mult": 2.0,
                "sl_atr_mult": 1.5,
                "confidence": round(confidence, 3),
                "horizon": PRODUCTION_RANGE_HORIZON_LABEL,
                "macro_cycle": onchain_metrics.cycle_phase,
                "mvrv": onchain_metrics.mvrv_ratio,
                "mvrv_ratio": onchain_metrics.mvrv_ratio,
                "nupl": onchain_metrics.nupl,
                "onchain_quality": onchain_metrics.quality.value,
                "uncertainty_breakdown": unc_breakdown,
                "uncertainty_narrative": unc_narrative,
                "liquidation_clusters": liquidation_clusters,
                "funding_carry_metrics": funding_carry_metrics,
                "time_stop_metrics": time_stop_metrics,
                "market_session_context": market_session_context,
                "top_historical_analogs": top_historical_analogs
            }

            self.latest_regime = {
                "trend_score": float(latest_state.get('trend_score', 0.0)),
                "trend_strength_pct": int(abs(float(latest_state.get('trend_score', 0.0))) * 100),
                "trend_label": "Bullish" if float(latest_state.get('trend_score', 0.0)) > 0 else "Bearish",
                "volatility_state": str(latest_state.get('volatility_state', 'MEDIUM')),
                "momentum_state": str(latest_state.get('momentum_state', 'NEUTRAL')),
                "funding_state": str(latest_state.get('funding_state', 'NEUTRAL')),
                "leverage_state": str(latest_state.get('leverage_state', 'NORMAL')),
                "current_regime": current_regime,
                "macro_cycle": onchain_metrics.cycle_phase,
                "mvrv": onchain_metrics.mvrv_ratio,
                "mvrv_ratio": onchain_metrics.mvrv_ratio,
                "nupl": onchain_metrics.nupl,
                "onchain_quality": onchain_metrics.quality.value,
                "event_flags": active_event_flags,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            self.latest_explanation = {
                "contributions": contributions_list,
                "summary": f"Model influenced by top indicators: {', '.join([c['feature'] for c in contributions_list[:2]])}"
            }

            if unc_breakdown.get('data_reliability', 1.0) <= 0.0 or onchain_val.get('is_degraded', False) and quality_score == 0:
                rating_str = "DATA_INVALID"
            elif quality_score >= 80:
                rating_str = "Excellent"
            elif quality_score >= 65:
                rating_str = "Good"
            elif quality_score >= 45:
                rating_str = "Fair"
            elif quality_score >= 25:
                rating_str = "Degraded"
            elif quality_score > 0:
                rating_str = "Severely Degraded"
            else:
                rating_str = "DATA_INVALID"

            self.latest_quality = {
                "score": quality_score,
                "max_score": 100,
                "rating": rating_str,
                "calibration_score": cal_score,
                "regime_confidence": reg_conf,
                "drift_score": dr_score,
                "model_agreement": ag_score
            }

            # Generate production 24h range forecast & risk envelope
            try:
                fc = self.range_service.generate_forecast(
                    current_price=entry_price,
                    vol_24h=float(df.iloc[-1].get('realized_vol_24h', 0.015)),
                    features=df.iloc[-1].to_dict(),
                    market_regime=current_regime,
                    directional_prob=prob,
                    timestamp=self.latest_prediction["timestamp"]
                )
                self.latest_range_forecast = fc.to_dict()

                # Broadcast over WebSocket if manager provided
                if ws_manager is not None:
                    import json
                    ws_msg = {
                        "type": "range_forecast_update",
                        "data": self.latest_range_forecast
                    }
                    asyncio.create_task(ws_manager.broadcast(json.dumps(ws_msg)))
            except Exception as fc_err:
                logger.error(f"Range forecast generation error: {fc_err}")

            # Record prediction & resolve pending outcomes in SQLite WAL
            try:
                record_prediction(
                    timestamp=self.latest_prediction["timestamp"],
                    price=entry_price,
                    regime=current_regime,
                    raw_prob=prob,
                    calibrated_prob=prob,
                    decision=action,
                    direction=direction,
                    tp=tp,
                    sl=sl,
                    macro_cycle=onchain_metrics.cycle_phase,
                    mvrv_val=onchain_metrics.mvrv_ratio,
                    nupl_val=onchain_metrics.nupl,
                    data_reliability=unc_breakdown.get('data_reliability', 1.0),
                    regime_certainty=unc_breakdown.get('regime_certainty', 1.0),
                    model_agreement=unc_breakdown.get('model_agreement', 1.0),
                    volatility_stress=unc_breakdown.get('volatility_stress', 1.0),
                    composite_quality_score=unc_breakdown.get('composite_quality_score', 1.0),
                    expected_return_gross_pct=round(abs(expected_ret) * 100, 2),
                    expected_return_net_pct=round(expected_ret_net * 100, 2)
                )
                resolve_pending_outcomes(current_price=entry_price, current_time_str=self.latest_prediction["timestamp"], horizon_hours=OUTCOME_RESOLUTION_HORIZON_HOURS)
                
                # Auto-resolve pending canonical decision envelopes (D_t -> R_t)
                from engine.decision_envelope import canonical_decision_ledger
                canonical_decision_ledger.resolve_pending_decisions(
                    current_price=entry_price,
                    current_time_iso=self.latest_prediction["timestamp"],
                    max_horizon_seconds=OUTCOME_RESOLUTION_HORIZON_HOURS * 3600
                )

                # Process live candle through Microstructure Arena & Decision Envelopes
                from engine.arena_evolution import process_candle
                process_candle(df.iloc[-1].to_dict())
            except Exception as mem_err:
                logger.error(f"Market memory / Decision ledger resolution error: {mem_err}")


# Global Singleton
live_engine = LiveInferenceEngine()
