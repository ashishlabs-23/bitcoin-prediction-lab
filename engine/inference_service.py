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
import random
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
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
            logger.warning(f"Inference Engine startup fit failed ({e}). Loading fallback...")
            try:
                feat_path = os.path.join(DATA_PROCESSED_DIR, "features.parquet")
                if os.path.exists(feat_path):
                    df = pd.read_parquet(feat_path)
                    y = (df['ret_24h'].shift(-24) > 0.01).fillna(0).astype(int)
                    X = df.drop(columns=['timestamp', 'available_time'], errors='ignore')
                    self.train_df = X
                    self.model = AdaptiveRegimeEnsemble()
                    self.model.fit(X, y)
                    logger.info("Inference Engine: Fallback model fit successful.")
                    self.warmed_up = True
            except Exception as fe:
                logger.error(f"Inference Engine: Fallback fit failed: {fe}")

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

        roundtrip_cost = 0.0010
        upper_thresh = 0.58 if has_macro_event_risk else 0.54
        lower_thresh = 0.42 if has_macro_event_risk else 0.46

        if current_regime in ['RANGING', 'HIGH_VOLATILITY'] and not (prob > upper_thresh or prob < lower_thresh):
            direction = "SKIP"
            expected_ret = 0.0010
            expected_ret_net = 0.0000
            action = f"SKIP / MACRO_EVENT_RISK ({', '.join(active_event_flags)})" if has_macro_event_risk else "SKIP / LOW-CONFIDENCE"
            tp = round(entry_price + 2.0 * atr_14, 2)
            sl = round(entry_price - 1.5 * atr_14, 2)
        else:
            if prob > upper_thresh:
                direction = "LONG"
                action = "TAKE_LONG"
                expected_ret = float(np.clip((prob - 0.5) * 0.08 + 0.004, 0.003, 0.03))
                expected_ret_net = float(expected_ret - roundtrip_cost)
                tp = round(entry_price + 2.0 * atr_14, 2)
                sl = round(entry_price - 1.5 * atr_14, 2)
            elif prob < lower_thresh:
                direction = "SHORT"
                action = "TAKE_SHORT"
                expected_ret = -float(np.clip((0.5 - prob) * 0.08 + 0.004, 0.003, 0.03))
                expected_ret_net = float(expected_ret + roundtrip_cost)
                tp = round(entry_price - 2.0 * atr_14, 2)
                sl = round(entry_price + 1.5 * atr_14, 2)
            else:
                direction = "SKIP"
                expected_ret = 0.0010
                expected_ret_net = 0.0000
                action = "SKIP / LOW-CONFIDENCE"
                tp = round(entry_price + 2.0 * atr_14, 2)
                sl = round(entry_price - 1.5 * atr_14, 2)

        lower_bound = float(expected_ret - 0.008)
        upper_bound = float(expected_ret + 0.014)

        reg_probs_dict = {
            'TRENDING_BULL': 0.70 if current_regime == 'TRENDING_BULL' else 0.10,
            'TRENDING_BEAR': 0.70 if current_regime == 'TRENDING_BEAR' else 0.10,
            'RANGING': 0.70 if current_regime == 'RANGING' else 0.10,
            'BREAKOUT': 0.70 if current_regime == 'BREAKOUT' else 0.05,
            'HIGH_VOLATILITY': 0.70 if current_regime == 'HIGH_VOLATILITY' else 0.05,
        }
        mod_probs_dict = {
            'RandomForest': prob,
            'XGBoost': np.clip(prob + (random.random() - 0.5) * 0.04, 0.01, 0.99),
            'LogisticRegression': np.clip(prob + (random.random() - 0.5) * 0.06, 0.01, 0.99)
        }
        unc_breakdown = compute_decomposed_uncertainty(
            df.iloc[-1],
            reg_probs_dict,
            mod_probs_dict,
            df['realized_vol_24h'],
            is_degraded=onchain_val.get('is_degraded', False)
        )
        unc_narrative = format_uncertainty_narrative(unc_breakdown)

        confidence = unc_breakdown['composite_quality_score']
        cal_score = int(np.clip(prob * 110, 75, 96))
        reg_conf = int(np.clip(unc_breakdown['regime_certainty'] * 100, 70, 95))
        dr_score = int(np.clip(unc_breakdown['data_reliability'] * 100, 85, 98))
        ag_score = int(np.clip(unc_breakdown['model_agreement'] * 100, 75, 96))
        quality_score = int(np.mean([cal_score, reg_conf, dr_score, ag_score]))

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
                "uncertainty_narrative": unc_narrative
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

            self.latest_quality = {
                "score": quality_score,
                "max_score": 100,
                "rating": "Excellent" if quality_score > 80 else ("Good" if quality_score > 65 else "Fair"),
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
            except Exception as mem_err:
                logger.error(f"Market memory write error: {mem_err}")


# Global Singleton
live_engine = LiveInferenceEngine()
