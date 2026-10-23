"""
engine/forecast_engine_15m.py — 15-Minute Forecast Engine & Non-Directional Research Baseline
=============================================================================================
Computes gap-safe features and research-only forward forecast projections on real Coinbase 15m data.

Key Invariants:
1. Data Readiness Separated from Model Readiness:
   - Data status: DATA_AVAILABLE (when validated 15m candles exist and are fresh)
   - Feature status: FEATURES_READY
   - Model status: MODEL_TIMEFRAME_INCOMPATIBLE (directional classifier is verified on hourly only)
   - Forecast status: FORECAST_AVAILABLE_RESEARCH_ONLY (empirical non-directional baseline & risk envelope)
   - Governance status: TIER 2 GATED (ABSTAIN)
   - Live trading: DISABLED
2. Genuine Forward Projection:
   - Origin marker at final completed candle t_0
   - Forward baseline points at t_0 + 900, t_0 + 1800, t_0 + 2700, t_0 + 3600
   - Upper and Lower uncertainty bands computed from empirical 15m volatility scaling with sqrt(t)
   - Zero synthetic fabrication: fails closed if 15m data is missing or stale.
"""

import os
import time
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from engine.coinbase_15m_adapter import coinbase_15m_adapter, GRANULARITY_15M


def _utc_iso(epoch_sec: float) -> str:
    return datetime.fromtimestamp(epoch_sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_15m_volatility(df: Optional[pd.DataFrame] = None, window: int = 32) -> Dict[str, Any]:
    """
    Computes Parkinson and close-to-close rolling volatility on 15-minute bars.
    """
    if df is None:
        cached = coinbase_15m_adapter.load_cached()
        if cached is None:
            df, _ = coinbase_15m_adapter.get_or_sync_15m_candles()
        else:
            df, _ = cached

    if len(df) < window:
        raise ValueError(f"Insufficient history: {len(df)} < {window}")

    recent = df.iloc[-window:].copy()
    
    # Close-to-close log returns
    closes = recent["close"].values
    log_rets = np.diff(np.log(closes))
    std_ret = float(np.std(log_rets, ddof=1)) if len(log_rets) > 1 else 0.005

    # Parkinson (High-Low) realized volatility
    # sigma_p^2 = (1 / (4 * ln 2)) * (ln(H/L))^2
    highs = recent["high"].values
    lows = recent["low"].values
    hl_ratio = np.log(highs / np.maximum(lows, 1e-8))
    parkinson_var = float(np.mean(hl_ratio ** 2) / (4.0 * math.log(2.0)))
    parkinson_vol = math.sqrt(max(1e-8, parkinson_var))

    # Annualized volatility factor (365 days * 24h * 4 bars/h = 35040 bars/year)
    bars_per_year = 35040.0
    vol_annualized = parkinson_vol * math.sqrt(bars_per_year)

    return {
        "status": "READY",
        "sigma_15m": round(parkinson_vol, 6),
        "parkinson_vol_15m": round(parkinson_vol, 6),
        "sigma_15m_ret": round(std_ret, 6),
        "annualized_vol_pct": round(vol_annualized * 100.0, 2),
        "volatility_annualized": round(vol_annualized, 4),
        "lookback_bars": window,
        "sample_size": window
    }


def generate_forecast_contract(
    horizon: str = "15m",
    steps_ahead: int = 4,
    num_steps: Optional[int] = None,
    confidence_level: float = 0.90
) -> Dict[str, Any]:
    """
    Generates a complete, typed forecast response contract for the requested horizon.
    Supports '15m' using real Coinbase 15m candles, and '1h'/'4h'/'24h' using verified hourly bars.
    """
    if num_steps is not None:
        steps_ahead = num_steps
    now_epoch = int(time.time())
    h_lower = str(horizon).lower().strip()

    if h_lower == "15m":
        granularity_sec = GRANULARITY_15M
        step_label = "15m"
        try:
            df, meta = coinbase_15m_adapter.get_or_sync_15m_candles(target_count=400, max_age_seconds=1800)
        except Exception as e:
            return {
                "status": "DATA_UNAVAILABLE",
                "data_readiness": "DATA_UNAVAILABLE",
                "model_readiness": "MODEL_TIMEFRAME_INCOMPATIBLE",
                "forecast_readiness": "FORECAST_NOT_AVAILABLE",
                "governance_state": "TIER 2 GATED (ABSTAIN)",
                "live_trading": "DISABLED",
                "source_timeframe": "15m",
                "reason": f"Failed fetching 15m market data from Coinbase: {str(e)}",
                "forecast_origin_timestamp": None,
                "forecast_points": [],
                "upper_band": [],
                "lower_band": []
            }
        
        if df.empty or len(df) < 32:
            return {
                "status": "DATA_UNAVAILABLE",
                "data_readiness": "DATA_UNAVAILABLE",
                "model_readiness": "MODEL_TIMEFRAME_INCOMPATIBLE",
                "forecast_readiness": "FORECAST_NOT_AVAILABLE",
                "governance_state": "TIER 2 GATED (ABSTAIN)",
                "live_trading": "DISABLED",
                "source_timeframe": "15m",
                "reason": "Insufficient 15-minute history available (requires >= 32 bars)",
                "forecast_origin_timestamp": None,
                "forecast_points": [],
                "upper_band": [],
                "lower_band": []
            }
        last_row = df.iloc[-1]
        origin_epoch = int(last_row["epoch_time"])
        origin_price = float(last_row["close"])
        vol_stats = compute_15m_volatility(df, window=32)
        base_vol = vol_stats["sigma_15m"]
        model_note = (
            "15-minute market data and features are verified. Production directional models "
            "(HAR-RS-DOW, TripleBarrierClassifier) remain HOURLY-ONLY. Directional signals remain ABSTAIN."
        )
        model_readiness = "MODEL_TIMEFRAME_INCOMPATIBLE"
    else:
        # Hourly / Macro horizons
        granularity_sec = 3600
        step_label = "1h"
        from engine.feature_cache import feature_cache
        df_h = feature_cache.get_features_df()
        if df_h.empty:
            # Fallback to reading data/raw/ohlcv.parquet
            ohlcv_path = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
            if os.path.exists(ohlcv_path):
                df_h = pd.read_parquet(ohlcv_path)
            else:
                return {
                    "status": "DATA_UNAVAILABLE",
                    "data_readiness": "DATA_UNAVAILABLE",
                    "model_readiness": "MODEL_TIMEFRAME_INCOMPATIBLE",
                    "forecast_readiness": "FORECAST_NOT_AVAILABLE",
                    "governance_state": "TIER 2 GATED (ABSTAIN)",
                    "live_trading": "DISABLED",
                    "source_timeframe": horizon,
                    "reason": "Hourly dataset unavailable",
                    "forecast_origin_timestamp": None,
                    "forecast_points": [],
                    "upper_band": [],
                    "lower_band": []
                }
        last_row = df_h.iloc[-1]
        ts_val = last_row.get("timestamp")
        if isinstance(ts_val, (pd.Timestamp, datetime)):
            origin_epoch = int(ts_val.timestamp())
        else:
            origin_epoch = int(time.time() // 3600) * 3600
        origin_price = float(last_row["close"])
        # Hourly rolling volatility (~0.0075 typical)
        closes = df_h["close"].tail(48).values
        rets = np.diff(np.log(closes))
        base_vol = float(np.std(rets, ddof=1)) if len(rets) > 1 else 0.0075
        vol_stats = {"sigma_1h": round(base_vol, 6), "lookback_bars": min(48, len(closes))}
        model_note = "Hourly verified market data. Directional model evaluated out-of-sample: ~52.1% accuracy, net expectancy negative after fees."
        model_readiness = "MODEL_DIRECTIONAL_GATED"

    origin_utc = _utc_iso(origin_epoch)
    data_age_sec = max(0, now_epoch - origin_epoch)

    # Conformal 90% multiplier
    z_mult = 1.645

    forecast_points = []
    upper_band = []
    lower_band = []

    # Include origin point for visual anchoring
    forecast_points.append({"time": origin_epoch, "price": origin_price, "value": origin_price, "is_origin": True})
    upper_band.append({"time": origin_epoch, "price": origin_price, "value": origin_price})
    lower_band.append({"time": origin_epoch, "price": origin_price, "value": origin_price})

    for h in range(1, steps_ahead + 1):
        step_time = origin_epoch + (h * granularity_sec)
        dispersion = z_mult * base_vol * math.sqrt(h)
        p_up = round(origin_price * math.exp(dispersion), 2)
        p_low = round(origin_price * math.exp(-dispersion), 2)

        forecast_points.append({
            "time": step_time,
            "price": origin_price,
            "value": origin_price,
            "is_origin": False,
            "step": h
        })
        upper_band.append({
            "time": step_time,
            "price": p_up,
            "value": p_up
        })
        lower_band.append({
            "time": step_time,
            "price": p_low,
            "value": p_low
        })

    decision_id = f"fc_{h_lower}_{origin_epoch}_{int(time.time())}"

    return {
        "status": "FORECAST_AVAILABLE_RESEARCH_ONLY",
        "forecast_id": decision_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Coinbase Exchange Spot REST",
        "instrument": "BTC-USD",
        "market_type": "spot",
        "source_timeframe": h_lower,
        "granularity_seconds": granularity_sec,
        "last_completed_candle_utc": origin_utc,
        "data_age_seconds": data_age_sec,
        "reference_price": origin_price,
        "reference_timestamp_utc": origin_utc,
        "forecast_horizon": h_lower,
        "target_definition": f"{h_lower} Non-Directional Persistence Baseline & Nominal Model Diffusion Envelope",
        "forecast_type": "NON_DIRECTIONAL_RESEARCH_BASELINE",
        "model_id": "EMPIRICAL_CONFORMAL_PERSISTENCE_v1.0",
        "model_version": "v1.0-research",
        "forecast_origin_timestamp": origin_epoch,
        "forecast_origin_utc": origin_utc,
        "points": forecast_points,
        "forecast_points": forecast_points,
        "upper_band": upper_band,
        "lower_band": lower_band,
        "confidence_level": confidence_level,
        "uncertainty_method": "Nominal Model-Based Diffusion Envelope (sqrt-time scaled; uncalibrated coverage)",
        "volatility_stats": vol_stats,
        "data_readiness": "DATA_AVAILABLE",
        "feature_readiness": "FEATURES_READY",
        "model_readiness": model_readiness,
        "model_compatibility_note": model_note,
        "forecast_readiness": "FORECAST_AVAILABLE_RESEARCH_ONLY",
        "product_mode": "ANALYSIS_ONLY",
        "live_trading_enabled": False,
        "order_submission_enabled": False,
        "directional_recommendation_status": "DISABLED",
        "price_forecast_status": "AVAILABLE",
        "directional_signal": "ABSTAIN",
        "directional_recommendation": "ABSTAIN",
        "governance_state": "TIER 2 GATED (ABSTAIN)",
        "governance_status": "TIER 2 GATED (ABSTAIN)",
        "live_trading": "DISABLED",
        "disclaimer": (
            "Research-only visualization. This non-directional persistence baseline and risk envelope "
            "does not constitute a directional return forecast or actionable trading signal."
        )
    }


def generate_15m_forecast_contract(
    steps_ahead: int = 4,
    confidence_level: float = 0.90,
    force_sync: bool = False
) -> Dict[str, Any]:
    """Backward compatibility alias for 15m forecast generation."""
    return generate_forecast_contract(horizon="15m", steps_ahead=steps_ahead, confidence_level=confidence_level)
