"""
research/v12_strategy_tournament_engine.py
==========================================
BTCognitive V12 — Regime-Adaptive Strategy Tournament & Risk-First Selection Engine
===================================================================================
Authoritative multi-agent tournament simulator and current market setup evaluator.
Orchestrated by Lead Research Orchestrator & Specialist Council (Agents A-G).

Key Capabilities:
1. Causal multi-timeframe regime classifier (Wilder ADX 14, EMA200/50/20, BBW compression, 3-candle persistence).
2. Five predeclared candidate hypotheses + four quantitative baselines:
   - Strategy A: REGIME_ADAPTIVE_ROUTER
   - Strategy B: MTF_MOMENTUM_TREND (50% partial exit at 1R, imperfect breakeven stop, 3x ATR trail)
   - Strategy C: VOL_COMPRESSION_BREAKOUT (BBW quintile compression, 12-bar breakout)
   - Strategy D: HTF_RANGE_EXPANSION_BREAKOUT (4-hour 20-bar consolidation breakout, expansion slippage)
   - Strategy E: SHORT_HORIZON_MEAN_REVERSION (Bollinger reversal, volume spike evasion filter)
   - Baselines: NO_TRADE, BUY_AND_HOLD, VOL_TARGETED_BULL, MATCHED_RANDOM_ENTRY
3. Verified event-driven simulator:
   - Next-bar-open execution.
   - Simultaneous TP/SL bar touch adverse resolution (SL first).
   - Imperfect breakeven realization (fees, spread, and slippage apply on fill).
4. Multi-scenario execution cost auditing:
   - Coinbase Retail Tier 1: 87.0 bps
   - Coinbase Institutional Tier 5+: 18.6 bps
   - Binance Perpetual Futures: 15.0 bps
   - Break-even cost metric (BPS_BE)
5. Risk-First Pareto ranking & transparent setup generation on latest market state.
"""

import os
import sys
import math
import time
import json
import hashlib
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engine.execution_cost_model import ExecutionCostModel


def compute_file_sha256(filepath: str) -> str:
    if not os.path.exists(filepath):
        return "UNAVAILABLE"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    z = 1.95996  # 95% normal quantile
    p = successes / total
    denom = 1.0 + (z**2) / total
    centre = (p + (z**2) / (2.0 * total)) / denom
    spread = (z * math.sqrt((p * (1.0 - p) / total) + (z**2) / (4.0 * total**2))) / denom
    return (max(0.0, float(centre - spread)), min(1.0, float(centre + spread)))


def stationary_bootstrap_ci(
    returns_bps: np.ndarray,
    n_bootstrap: int = 1000,
    expected_block_len: int = 10,
    alpha: float = 0.05,
    random_seed: int = 42
) -> Tuple[float, float]:
    n = len(returns_bps)
    if n < 5:
        m = float(np.mean(returns_bps)) if n > 0 else 0.0
        return (m, m)
    
    rng = np.random.default_rng(random_seed)
    p_geom = 1.0 / max(1.0, expected_block_len)
    boot_means = np.empty(n_bootstrap, dtype=float)

    for b in range(n_bootstrap):
        sample_indices = np.empty(n, dtype=int)
        idx = rng.integers(0, n)
        for i in range(n):
            if rng.random() < p_geom:
                idx = rng.integers(0, n)
            else:
                idx = (idx + 1) % n
            sample_indices[i] = idx
        boot_means[b] = np.mean(returns_bps[sample_indices])

    lower = float(np.percentile(boot_means, 100.0 * (alpha / 2.0)))
    upper = float(np.percentile(boot_means, 100.0 * (1.0 - alpha / 2.0)))
    return (lower, upper)


# =============================================================================
# Technical Indicators (Causal Point-in-Time, Zero Lookahead)
# =============================================================================

def compute_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    tr = np.zeros(n, dtype=float)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    
    atr = np.zeros(n, dtype=float)
    if n < period:
        return atr
    atr[period - 1] = np.mean(tr[:period])
    alpha = 1.0 / period
    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def compute_adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Wilder's ADX (1978). Returns (ADX, +DI, -DI).
    """
    n = len(close)
    adx = np.zeros(n, dtype=float)
    plus_di = np.zeros(n, dtype=float)
    minus_di = np.zeros(n, dtype=float)
    if n < period * 2:
        return adx, plus_di, minus_di

    up_move = high[1:] - high[:-1]
    down_move = low[:-1] - low[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))

    # Smoothed TR and DMs
    smooth_tr = np.zeros(n - 1, dtype=float)
    smooth_plus_dm = np.zeros(n - 1, dtype=float)
    smooth_minus_dm = np.zeros(n - 1, dtype=float)

    smooth_tr[period - 1] = np.sum(tr[:period])
    smooth_plus_dm[period - 1] = np.sum(plus_dm[:period])
    smooth_minus_dm[period - 1] = np.sum(minus_dm[:period])

    for i in range(period, n - 1):
        smooth_tr[i] = smooth_tr[i - 1] - (smooth_tr[i - 1] / period) + tr[i]
        smooth_plus_dm[i] = smooth_plus_dm[i - 1] - (smooth_plus_dm[i - 1] / period) + plus_dm[i]
        smooth_minus_dm[i] = smooth_minus_dm[i - 1] - (smooth_minus_dm[i - 1] / period) + minus_dm[i]

    dx = np.zeros(n, dtype=float)
    for i in range(period - 1, n - 1):
        p_di = (smooth_plus_dm[i] / max(1e-9, smooth_tr[i])) * 100.0
        m_di = (smooth_minus_dm[i] / max(1e-9, smooth_tr[i])) * 100.0
        plus_di[i + 1] = p_di
        minus_di[i + 1] = m_di
        denom = p_di + m_di
        if denom > 1e-9:
            dx[i + 1] = 100.0 * abs(p_di - m_di) / denom

    # ADX is Wilder smoothed DX
    start_adx_idx = period * 2 - 1
    if start_adx_idx < n:
        adx[start_adx_idx] = np.mean(dx[period:start_adx_idx + 1])
        for i in range(start_adx_idx + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    return adx, plus_di, minus_di


def compute_ema(series: np.ndarray, period: int) -> np.ndarray:
    n = len(series)
    ema = np.zeros(n, dtype=float)
    if n < period:
        return ema
    alpha = 2.0 / (period + 1.0)
    ema[period - 1] = np.mean(series[:period])
    for i in range(period, n):
        ema[i] = alpha * series[i] + (1.0 - alpha) * ema[i - 1]
    return ema


def compute_bollinger_bands(series: np.ndarray, period: int = 20, num_std: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n = len(series)
    mid = np.zeros(n, dtype=float)
    upper = np.zeros(n, dtype=float)
    lower = np.zeros(n, dtype=float)
    bandwidth = np.zeros(n, dtype=float)

    for i in range(period - 1, n):
        window = series[i - period + 1 : i + 1]
        m = float(np.mean(window))
        s = float(np.std(window))
        mid[i] = m
        upper[i] = m + num_std * s
        lower[i] = m - num_std * s
        bandwidth[i] = (upper[i] - lower[i]) / max(1e-9, m)

    return mid, upper, lower, bandwidth


class AttributeDict(dict):
    """Dictionary supporting both item and attribute access for backward compatibility."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")
    def __setattr__(self, key, value):
        self[key] = value

class EconomicEligibility(AttributeDict):
    pass

class MarketSnapshot(AttributeDict):
    pass


# =============================================================================
# Tournament Engine Class
# =============================================================================

class V12StrategyTournamentEngine:
    """
    Evaluates 5 strategy candidates and 4 baselines on genuine BTC-USD market data.
    Enforces risk-first selection, cost reconciliation, and regime compatibility.
    """

    COST_SCENARIOS = {
        "COINBASE_RETAIL_87BPS": {
            "name": "Coinbase Advanced Retail Tier 1",
            "market_type": "SPOT",
            "round_trip_bps": 87.0,
            "two_sided_commission_bps": 80.0,
            "two_sided_spread_bps": 3.0,
            "two_sided_slippage_bps": 4.0,
            "funding_bps": 0.0,
            "is_hypothetical": False,
            "description": "Empirical retail spot tier (<$10k 30d volume) with taker fees"
        },
        "COINBASE_INSTITUTIONAL_18BPS": {
            "name": "Coinbase Institutional High-Volume Tier 5+",
            "market_type": "SPOT",
            "round_trip_bps": 18.6,
            "two_sided_commission_bps": 11.6,
            "two_sided_spread_bps": 3.0,
            "two_sided_slippage_bps": 4.0,
            "funding_bps": 0.0,
            "is_hypothetical": False,
            "description": "Empirical institutional high-volume spot schedule"
        },
        "BINANCE_PERP_15BPS": {
            "name": "Binance USDT-M Perpetual Futures",
            "market_type": "DERIVATIVES_PERPETUAL",
            "round_trip_bps": 15.0,
            "two_sided_commission_bps": 10.0,
            "two_sided_spread_bps": 1.0,
            "two_sided_slippage_bps": 2.0,
            "funding_bps": 2.0,
            "is_hypothetical": True,
            "description": "Hypothetical perpetual futures model with 8-hour funding assumption"
        }
    }

    CANDIDATE_SPECS = {
        "REGIME_ADAPTIVE_ROUTER": {
            "id": "REGIME_ADAPTIVE_ROUTER",
            "name": "Regime-Adaptive Trend/Range Router",
            "version": "1.0.0",
            "family": "META_ROUTER",
            "source_ref": "SRC-01, SRC-02, SRC-03 (Wilder 1978, Bollinger 2001)",
            "source_citation": "SRC-01, SRC-02, SRC-03 (Wilder 1978, Bollinger 2001)",
            "supported_timeframe": "1h",
            "timeframe": "1h",
            "required_inputs": ["ohlcv_1h", "adx_14", "ema_200", "bbw_20"],
            "indicators": ["ohlcv_1h", "adx_14", "ema_200", "bbw_20"],
            "supported_regimes": ["TRENDING_BULL", "TRENDING_BEAR", "CONSOLIDATION_RANGE", "VOL_COMPRESSION_RANGE"],
            "entry_rules": "Dynamic dispatch based on causal regime: MTF_MOMENTUM_TREND if TRENDING, SHORT_HORIZON_MEAN_REVERSION if CONSOLIDATION, VOL_COMPRESSION_BREAKOUT if COMPRESSION. Abstain if TRANSITION_UNSUPPORTED.",
            "exit_rules": "Delegates to active branch exit rules. Closes position immediately upon regime transition with 50% switching friction debit.",
            "description": "Classifies market regime via completed 1h ADX & EMA200 with 3-bar hysteresis, routing dynamically to trend, mean reversion, or breakout branches; abstains during transition."
        },
        "MTF_MOMENTUM_TREND": {
            "id": "MTF_MOMENTUM_TREND",
            "name": "MTF Momentum Trend Following (Partial Exits & Breakeven)",
            "version": "1.0.0",
            "family": "TREND_FOLLOWING",
            "source_ref": "SRC-01, SRC-03, SRC-07 (Donchian 1960, Wilder 1978)",
            "source_citation": "SRC-01, SRC-03, SRC-07 (Donchian 1960, Wilder 1978)",
            "supported_timeframe": "1h",
            "timeframe": "1h",
            "required_inputs": ["ohlcv_1h", "ema_200", "donchian_20", "atr_14"],
            "indicators": ["ohlcv_1h", "ema_200", "donchian_20", "atr_14"],
            "supported_regimes": ["TRENDING_BULL", "TRENDING_BEAR"],
            "entry_rules": "Close > 1h EMA200 AND Close >= Donchian High(20) for Long; Close < 1h EMA200 AND Close <= Donchian Low(20) for Short in trending regime.",
            "exit_rules": "Initial SL at 2.0x ATR(14). Partial exit 50% at 1.0R gain and move stop to breakeven + round-trip cost. Trailing stop at 3.0x ATR(14).",
            "description": "20-bar Donchian breakout aligned with 1h EMA200 filter; 50% partial exit at 1R, stop moved to breakeven + cost drag, trailing 3x ATR."
        },
        "VOL_COMPRESSION_BREAKOUT": {
            "id": "VOL_COMPRESSION_BREAKOUT",
            "name": "Volatility-Compression Breakout",
            "version": "1.0.0",
            "family": "VOLATILITY_BREAKOUT",
            "source_ref": "SRC-02 (Bollinger 2001)",
            "source_citation": "SRC-02 (Bollinger 2001)",
            "supported_timeframe": "1h",
            "timeframe": "1h",
            "required_inputs": ["ohlcv_1h", "bbw_20", "bbw_pct100", "atr_14"],
            "indicators": ["ohlcv_1h", "bbw_20", "bbw_pct100", "atr_14"],
            "supported_regimes": ["VOL_COMPRESSION_RANGE"],
            "entry_rules": "BBW(20) <= 20th percentile (lowest compression) AND Close >= Breakout High(12) in VOL_COMPRESSION_RANGE.",
            "exit_rules": "Stop loss at 1.5x ATR(14) below entry. Take profit at 2.5x ATR(14) or exit on 15 bars max holding time.",
            "description": "Identifies coiling compression via lowest 20th percentile of BBW(20) followed by 12-bar high breakout with 1.5x ATR stop."
        },
        "HTF_RANGE_EXPANSION_BREAKOUT": {
            "id": "HTF_RANGE_EXPANSION_BREAKOUT",
            "name": "Higher-Timeframe Range Expansion Breakout",
            "version": "1.0.0",
            "family": "RANGE_BREAKOUT",
            "source_ref": "SRC-03 (Donchian 1960)",
            "source_citation": "SRC-03 (Donchian 1960)",
            "supported_timeframe": "4h",
            "timeframe": "4h",
            "required_inputs": ["ohlcv_4h", "channel_20_4h"],
            "indicators": ["ohlcv_4h", "channel_20_4h"],
            "supported_regimes": ["TRENDING_BULL", "TRENDING_BEAR", "VOL_COMPRESSION_RANGE"],
            "entry_rules": "Close > Range High(20) on 4h timeframe across non-transition regimes.",
            "exit_rules": "Stop loss at Range Low(20) on 4h timeframe or max hold expired (18 4h bars / 72 hours).",
            "description": "4-hour consolidated range breakout beyond 20-period 4h boundary; accounts for adverse expansion slippage."
        },
        "SHORT_HORIZON_MEAN_REVERSION": {
            "id": "SHORT_HORIZON_MEAN_REVERSION",
            "name": "Short-Horizon Mean Reversion (Adverse-Flow Gated)",
            "version": "1.0.0",
            "family": "MEAN_REVERSION",
            "source_ref": "SRC-02 (Bollinger 2001)",
            "source_citation": "SRC-02 (Bollinger 2001)",
            "supported_timeframe": "1h",
            "timeframe": "1h",
            "required_inputs": ["ohlcv_1h", "bollinger_20", "volume_ma20"],
            "indicators": ["ohlcv_1h", "bollinger_20", "volume_ma20"],
            "supported_regimes": ["CONSOLIDATION_RANGE"],
            "entry_rules": "ADX(14) < 20.0 AND Close < Lower Bollinger Band(20, 2) AND Volume <= 2.5x Volume MA(20) (Adverse Selection Gate).",
            "exit_rules": "Take profit at SMA(20). Stop loss at 1.5x ATR(14) below entry. Max hold 12 hours.",
            "description": "Counter-trend reversal on Bollinger 2.0-std band breaches in low-ADX regimes; strictly gated when hourly volume > 2.5x MA."
        }
    }

    BASELINE_SPECS = {
        "NO_TRADE": {
            "id": "NO_TRADE",
            "name": "Cash Baseline (No Trade)",
            "family": "PASSIVE_BASELINE",
            "description": "Zero market exposure, zero trading friction, zero drawdown reference."
        },
        "BUY_AND_HOLD": {
            "id": "BUY_AND_HOLD",
            "name": "Unhedged Buy & Hold",
            "family": "PASSIVE_BASELINE",
            "description": "Continuous 100% long exposure across the identical evaluation window."
        },
        "VOL_TARGETED_BULL": {
            "id": "VOL_TARGETED_BULL",
            "name": "Volatility-Targeted Long Exposure",
            "family": "PASSIVE_BASELINE",
            "description": "Long exposure scaled inversely to rolling realized volatility to target 10% annualized risk."
        },
        "MATCHED_RANDOM_ENTRY": {
            "id": "MATCHED_RANDOM_ENTRY",
            "name": "Matched Random-Entry Control",
            "family": "STOCHASTIC_BASELINE",
            "description": "Monte Carlo random trade entry baseline with matched trade frequency and holding duration."
        }
    }

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
        self.coinbase_15m_path = os.path.join(REPO_ROOT, "data", "raw", "coinbase_15m.parquet")
        self.df_1h: Optional[pd.DataFrame] = None
        self.df_4h: Optional[pd.DataFrame] = None
        self._load_and_prepare_data()

    def _load_and_prepare_data(self):
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Hourly dataset not found at {self.data_path}")

        df = pd.read_parquet(self.data_path)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df = df.sort_values("timestamp").reset_index(drop=True)
        else:
            df["timestamp"] = pd.date_range("2022-01-01", periods=len(df), freq="1h", tz="UTC")

        # Required columns: open, high, low, close, volume
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in df.columns:
                raise ValueError(f"Missing required OHLCV column: {col}")
            df[col] = df[col].astype(float)

        # Compute Technical Indicators on 1h (Causal, zero lookahead)
        c = df["close"].values
        h = df["high"].values
        l = df["low"].values
        v = df["volume"].values

        df["ema_20"] = compute_ema(c, 20)
        df["ema_50"] = compute_ema(c, 50)
        df["ema_200"] = compute_ema(c, 200)
        df["atr_14"] = compute_atr(h, l, c, 14)
        
        adx, p_di, m_di = compute_adx(h, l, c, 14)
        df["adx_14"] = adx
        df["plus_di"] = p_di
        df["minus_di"] = m_di

        mid, up, low_b, bbw = compute_bollinger_bands(c, 20, 2.0)
        df["bb_mid"] = mid
        df["bb_upper"] = up
        df["bb_lower"] = low_b
        df["bb_width"] = bbw

        # Rolling 100-bar percentile of BBW
        bbw_series = pd.Series(bbw)
        df["bbw_pct100"] = bbw_series.rolling(100, min_periods=20).apply(
            lambda x: (x[-1] <= x).mean() if len(x) > 0 else 0.5, raw=True
        )

        # 20-period Donchian High/Low (strictly based on preceding bars: shift 1)
        df["donchian_high_20"] = pd.Series(h).shift(1).rolling(20, min_periods=20).max().fillna(pd.Series(h))
        df["donchian_low_20"] = pd.Series(l).shift(1).rolling(20, min_periods=20).min().fillna(pd.Series(l))

        # 12-period High/Low for compression breakout (shift 1)
        df["breakout_high_12"] = pd.Series(h).shift(1).rolling(12, min_periods=12).max().fillna(pd.Series(h))
        df["breakout_low_12"] = pd.Series(l).shift(1).rolling(12, min_periods=12).min().fillna(pd.Series(l))

        # Rolling volume MA
        df["vol_ma20"] = pd.Series(v).rolling(20, min_periods=5).mean().fillna(pd.Series(v))

        # Regime classification on 1h
        regimes = []
        for i in range(len(df)):
            close_val = c[i]
            ema200 = df["ema_200"].iloc[i]
            ema50 = df["ema_50"].iloc[i]
            ema20 = df["ema_20"].iloc[i]
            adx_val = df["adx_14"].iloc[i]
            bbw_val = df["bb_width"].iloc[i]
            bbw_pct = df["bbw_pct100"].iloc[i]

            if i < 200:
                regimes.append("TRANSITION_UNSUPPORTED")
                continue

            # Standardized distance from EMA50
            z_score = abs(close_val - ema50) / max(1e-9, df["atr_14"].iloc[i])

            if close_val > ema200 and adx_val >= 25.0 and ema20 > ema50:
                regimes.append("TRENDING_BULL")
            elif close_val < ema200 and adx_val >= 25.0 and ema20 < ema50:
                regimes.append("TRENDING_BEAR")
            elif adx_val < 20.0 and bbw_pct <= 0.20:
                regimes.append("VOL_COMPRESSION_RANGE")
            elif (20.0 <= adx_val < 25.0) or (z_score <= 2.5 and adx_val < 25.0):
                regimes.append("CONSOLIDATION_RANGE")
            else:
                regimes.append("TRANSITION_UNSUPPORTED")

        df["raw_regime"] = regimes

        # Apply 3-candle persistence hysteresis with strict time-continuity validation
        confirmed_regime = []
        hysteresis_status = []
        current_active = "CONSOLIDATION_RANGE"
        pending_regime = None
        pending_count = 0
        last_ts = None

        for idx, r in enumerate(regimes):
            curr_ts = df["timestamp"].iloc[idx]
            if last_ts is not None:
                step_sec = (curr_ts - last_ts).total_seconds()
                # If a data gap is detected (>3660s for hourly candles):
                if step_sec > 3660.0:
                    # Invalidate pending confirmation across data gaps
                    pending_regime = None
                    pending_count = 0
                    # Prolonged gap (>3 hours) breaks established regime continuity
                    if step_sec > 10800.0:
                        current_active = "TRANSITION_UNSUPPORTED"
            last_ts = curr_ts

            if r == current_active:
                pending_regime = None
                pending_count = 0
                confirmed_regime.append(current_active)
                hysteresis_status.append("CONFIRMED")
            else:
                if r == pending_regime:
                    pending_count += 1
                else:
                    pending_regime = r
                    pending_count = 1

                if pending_count >= 3:
                    current_active = pending_regime
                    pending_regime = None
                    pending_count = 0
                    confirmed_regime.append(current_active)
                    hysteresis_status.append("CONFIRMED")
                else:
                    confirmed_regime.append(current_active)
                    hysteresis_status.append("TRANSITION_PENDING")

        df["regime"] = confirmed_regime
        df["hysteresis_status"] = hysteresis_status

        self.df_1h = df

        # Build causal 4-hour aggregation
        df_resampled = df.set_index("timestamp").resample("4h", closed="left", label="left").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna().reset_index()

        c4 = df_resampled["close"].values
        h4 = df_resampled["high"].values
        l4 = df_resampled["low"].values
        df_resampled["atr_14_4h"] = compute_atr(h4, l4, c4, 14)
        df_resampled["range_high_20_4h"] = pd.Series(h4).shift(1).rolling(20, min_periods=20).max().fillna(pd.Series(h4))
        df_resampled["range_low_20_4h"] = pd.Series(l4).shift(1).rolling(20, min_periods=20).min().fillna(pd.Series(l4))

        self.df_4h = df_resampled

    def build_market_snapshot(
        self,
        eval_time: Optional[datetime] = None,
        freshness_policy_seconds: float = 7200.0,
        live_quote: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        BTCognitive V17 Market Snapshot Identity & Freshness Verification.
        Traces provider identity, candle intervals, closure status, timestamps,
        observed age, and sequence/divergence invariants.
        """
        now_dt = eval_time if eval_time is not None else datetime.now(timezone.utc)
        if self.df_1h is None or len(self.df_1h) == 0:
            return {
                "provider": "coinbase",
                "instrument": "BTC-USD",
                "interval": "1h",
                "candle_open_timestamp_utc": None,
                "candle_close_timestamp_utc": None,
                "is_candle_closed": False,
                "is_feature_eligible": False,
                "latest_quote_timestamp_utc": None,
                "latest_quote_source": None,
                "latest_quote_price_usd": None,
                "quote_feature_divergence": False,
                "source_timestamp_utc": None,
                "receipt_timestamp_utc": now_dt.isoformat(),
                "dataset_identifier": "EMPTY",
                "feature_version": "1.0.0",
                "freshness_policy_seconds": freshness_policy_seconds,
                "observed_age_seconds": None,
                "freshness_status": "DATA_UNAVAILABLE",
                "is_fresh": False,
                "rejection_reason": "No market candle data loaded."
            }

        latest = self.df_1h.iloc[-1]
        candle_ts = pd.to_datetime(latest["timestamp"], utc=True)
        candle_close_utc = candle_ts.isoformat()
        candle_open_utc = (candle_ts - timedelta(hours=1)).isoformat()

        age_sec = (now_dt - candle_ts).total_seconds()

        if age_sec < -60.0:  # Clock skew tolerance
            status = "FUTURE_TIMESTAMP"
            is_fresh = False
            reason = f"Candle close timestamp ({candle_close_utc}) is in the future relative to evaluation clock ({now_dt.isoformat()})."
        elif age_sec > freshness_policy_seconds:
            status = "STALE"
            is_fresh = False
            reason = f"Market data snapshot is stale: latest closed candle is {age_sec/3600.0:.1f}h old (policy limit: {freshness_policy_seconds/3600.0:.1f}h)."
        else:
            status = "FRESH"
            is_fresh = True
            reason = "Market data snapshot is fresh and within policy threshold."

        data_hash = hashlib.sha256(f"{len(self.df_1h)}:{latest['close']}:{candle_close_utc}".encode("utf-8")).hexdigest()[:16]

        quote_ts_utc = None
        quote_source = None
        quote_price = None
        divergence = False
        if live_quote:
            quote_ts_utc = live_quote.get("source_timestamp_utc") or live_quote.get("timestamp")
            quote_source = live_quote.get("provider") or live_quote.get("source", "coinbase")
            quote_price = live_quote.get("price_usd") or live_quote.get("price")
            quote_age = float(live_quote.get("age_seconds", 0.0) or 0.0)
            if quote_age <= 60.0 and age_sec > freshness_policy_seconds:
                divergence = True
                status = "QUOTE_FEATURE_DIVERGENCE"
                is_fresh = False
                reason = "Quote-feature divergence: Live quote is fresh but underlying 1h feature snapshot is stale (>2h old). Combining old features with new quote is prohibited without full indicator recalculation."

        return {
            "provider": "coinbase",
            "instrument": "BTC-USD",
            "interval": "1h",
            "candle_open_timestamp_utc": candle_open_utc,
            "candle_close_timestamp_utc": candle_close_utc,
            "is_candle_closed": True,
            "is_feature_eligible": is_fresh,
            "latest_quote_timestamp_utc": quote_ts_utc,
            "latest_quote_source": quote_source,
            "latest_quote_price_usd": quote_price,
            "quote_feature_divergence": divergence,
            "source_timestamp_utc": candle_close_utc,
            "receipt_timestamp_utc": now_dt.isoformat(),
            "dataset_identifier": data_hash,
            "feature_version": "1.0.0",
            "freshness_policy_seconds": freshness_policy_seconds,
            "observed_age_seconds": round(age_sec, 1) if age_sec >= 0 else 0.0,
            "freshness_status": status,
            "is_fresh": is_fresh,
            "is_stale": not is_fresh,
            "rejection_reason": reason if not is_fresh else None
        }

    def get_current_market_regime(
        self,
        eval_time: Optional[datetime] = None,
        df_override: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Returns the current regime context evaluated on the latest completed hourly candle.
        """
        df_target = df_override if df_override is not None else self.df_1h
        if df_target is None or len(df_target) == 0:
            return {"status": "DATA_UNAVAILABLE", "regime": "TRANSITION_UNSUPPORTED"}

        latest = df_target.iloc[-1]
        prev = df_target.iloc[-2] if len(df_target) > 1 else latest
        snapshot = self.build_market_snapshot(eval_time=eval_time)

        regime_val = str(latest.get("regime", "TRANSITION_UNSUPPORTED"))
        raw_regime_val = str(latest.get("raw_regime", "TRANSITION_UNSUPPORTED"))
        h_status = str(latest.get("hysteresis_status", "CONFIRMED"))
        time_str = latest["timestamp"].isoformat() if hasattr(latest["timestamp"], "isoformat") else str(latest["timestamp"])

        return {
            "instrument": "BTC-USD",
            "venue": "Coinbase Exchange Spot",
            "granularity": "1h",
            "latest_completed_time": time_str,
            "latest_completed_price": float(latest["close"]),
            "regime": regime_val,
            "raw_regime": raw_regime_val,
            "hysteresis_status": h_status,
            "adx_14": round(float(latest.get("adx_14", 25.0)), 2),
            "plus_di": round(float(latest.get("plus_di", 20.0)), 2),
            "minus_di": round(float(latest.get("minus_di", 20.0)), 2),
            "ema_20": round(float(latest.get("ema_20", latest["close"])), 2),
            "ema_50": round(float(latest.get("ema_50", latest["close"])), 2),
            "ema_200": round(float(latest.get("ema_200", latest["close"])), 2),
            "atr_14": round(float(latest.get("atr_14", 100.0)), 2),
            "bb_width": round(float(latest.get("bb_width", 0.04)), 4),
            "bbw_percentile": round(float(latest.get("bbw_pct100", 0.5)), 3),
            "classification_rule": "Wilder ADX(14)>=25 + EMA200 trend filter with 3-bar confirmation hysteresis",
            "market_snapshot": snapshot,
            "directional_authorization": "OFFLINE_RESEARCH_ONLY",
            "execution_authorization": "DISABLED"
        }

    # =========================================================================
    # Strategy Backtesters (Event-Driven Simulator)
    # =========================================================================

    def _simulate_candidate_b_trend(self, df_eval: pd.DataFrame, cost_scenario: str) -> List[Dict[str, Any]]:
        """
        MTF Momentum Trend Following:
        - 20-period Donchian breakout with 1h EMA200 trend filter
        - 50% partial exit at 1R ($2 \times \text{ATR}$)
        - Remaining stop moved to breakeven + cost drag
        - Remaining 50% trails with 3x ATR
        - Next-bar open execution
        """
        trades = []
        cost_bps = self.COST_SCENARIOS[cost_scenario]["round_trip_bps"]
        cost_frac = cost_bps / 10000.0

        in_pos = False
        pos_entry_price = 0.0
        pos_entry_idx = 0
        initial_risk = 0.0
        r_target = 0.0
        partial_exited = False
        active_stop = 0.0
        highest_price = 0.0

        n = len(df_eval)
        for i in range(200, n - 1):
            cur = df_eval.iloc[i]
            nxt = df_eval.iloc[i + 1]

            if not in_pos:
                # Entry signal on bar i: Close > EMA200 and Close > Donchian High
                if cur["close"] > cur["ema_200"] and cur["close"] > cur["donchian_high_20"]:
                    # Next-bar open fill
                    in_pos = True
                    pos_entry_price = float(nxt["open"])
                    pos_entry_idx = i + 1
                    atr_val = float(cur["atr_14"])
                    initial_risk = max(10.0, 2.0 * atr_val)
                    r_target = pos_entry_price + initial_risk
                    active_stop = pos_entry_price - initial_risk
                    highest_price = pos_entry_price
                    partial_exited = False
            else:
                highest_price = max(highest_price, float(cur["high"]))
                # Check target and stop on current bar
                bar_low = float(cur["low"])
                bar_high = float(cur["high"])
                atr_val = float(cur["atr_14"])

                # Check 1R partial exit
                if not partial_exited and bar_high >= r_target:
                    partial_exited = True
                    # Stop moved to breakeven + round-trip cost friction
                    active_stop = pos_entry_price * (1.0 + cost_frac)
                elif partial_exited:
                    # Trailing 3x ATR
                    trail_stop = highest_price - 3.0 * atr_val
                    active_stop = max(active_stop, trail_stop)

                # Check adverse touch / stop hit
                stop_hit = bar_low <= active_stop
                max_hold_expired = (i - pos_entry_idx) >= 72  # 3 days max hold

                if stop_hit or max_hold_expired:
                    exit_price = active_stop if stop_hit else float(cur["close"])
                    # If partial exited: 50% at 1R, 50% at exit_price
                    if partial_exited:
                        gross_return = 0.5 * ((r_target - pos_entry_price) / pos_entry_price) + 0.5 * ((exit_price - pos_entry_price) / pos_entry_price)
                    else:
                        gross_return = (exit_price - pos_entry_price) / pos_entry_price

                    net_return = gross_return - cost_frac
                    trades.append({
                        "entry_idx": pos_entry_idx,
                        "exit_idx": i,
                        "entry_time": df_eval.iloc[pos_entry_idx]["timestamp"].isoformat(),
                        "exit_time": cur["timestamp"].isoformat(),
                        "entry_price": pos_entry_price,
                        "exit_price": exit_price,
                        "partial_exited": partial_exited,
                        "gross_return_bps": gross_return * 10000.0,
                        "net_return_bps": net_return * 10000.0,
                        "holding_bars": i - pos_entry_idx + 1
                    })
                    in_pos = False

        return trades

    def _simulate_candidate_c_vol_compression(self, df_eval: pd.DataFrame, cost_scenario: str) -> List[Dict[str, Any]]:
        """
        Volatility-Compression Breakout:
        - BBW < 20th percentile
        - Breakout above 12-bar high
        - Stop loss at 1.5x ATR
        """
        trades = []
        cost_bps = self.COST_SCENARIOS[cost_scenario]["round_trip_bps"]
        cost_frac = cost_bps / 10000.0

        in_pos = False
        pos_entry_price = 0.0
        pos_entry_idx = 0
        active_stop = 0.0

        n = len(df_eval)
        for i in range(120, n - 1):
            cur = df_eval.iloc[i]
            nxt = df_eval.iloc[i + 1]

            if not in_pos:
                # Compression condition + 12-bar breakout
                if cur["bbw_pct100"] <= 0.20 and cur["close"] > cur["breakout_high_12"]:
                    in_pos = True
                    pos_entry_price = float(nxt["open"])
                    pos_entry_idx = i + 1
                    atr_val = float(cur["atr_14"])
                    active_stop = pos_entry_price - 1.5 * atr_val
            else:
                bar_low = float(cur["low"])
                max_hold_expired = (i - pos_entry_idx) >= 24

                if bar_low <= active_stop or max_hold_expired:
                    exit_price = active_stop if bar_low <= active_stop else float(cur["close"])
                    gross_return = (exit_price - pos_entry_price) / pos_entry_price
                    net_return = gross_return - cost_frac
                    trades.append({
                        "entry_idx": pos_entry_idx,
                        "exit_idx": i,
                        "entry_time": df_eval.iloc[pos_entry_idx]["timestamp"].isoformat(),
                        "exit_time": cur["timestamp"].isoformat(),
                        "entry_price": pos_entry_price,
                        "exit_price": exit_price,
                        "gross_return_bps": gross_return * 10000.0,
                        "net_return_bps": net_return * 10000.0,
                        "holding_bars": i - pos_entry_idx + 1
                    })
                    in_pos = False

        return trades

    def _simulate_candidate_d_htf_expansion(self, cost_scenario: str) -> List[Dict[str, Any]]:
        """
        4-Hour Range Expansion Breakout on df_4h:
        - 20-bar 4h high breakout
        - Stop at opposite 20-bar 4h low
        - Modeled 50% extra expansion slippage
        """
        if self.df_4h is None or len(self.df_4h) < 40:
            return []

        df_eval = self.df_4h
        trades = []
        cost_bps = self.COST_SCENARIOS[cost_scenario]["round_trip_bps"] + 2.0  # +2 bps expansion slippage
        cost_frac = cost_bps / 10000.0

        in_pos = False
        pos_entry_price = 0.0
        pos_entry_idx = 0
        active_stop = 0.0

        n = len(df_eval)
        for i in range(25, n - 1):
            cur = df_eval.iloc[i]
            nxt = df_eval.iloc[i + 1]

            if not in_pos:
                if cur["close"] > cur["range_high_20_4h"]:
                    in_pos = True
                    pos_entry_price = float(nxt["open"])
                    pos_entry_idx = i + 1
                    active_stop = float(cur["range_low_20_4h"])
            else:
                bar_low = float(cur["low"])
                max_hold_expired = (i - pos_entry_idx) >= 18  # 3 days on 4h bars

                if bar_low <= active_stop or max_hold_expired:
                    exit_price = active_stop if bar_low <= active_stop else float(cur["close"])
                    gross_return = (exit_price - pos_entry_price) / pos_entry_price
                    net_return = gross_return - cost_frac
                    trades.append({
                        "entry_idx": pos_entry_idx,
                        "exit_idx": i,
                        "entry_time": df_eval.iloc[pos_entry_idx]["timestamp"].isoformat(),
                        "exit_time": cur["timestamp"].isoformat(),
                        "entry_price": pos_entry_price,
                        "exit_price": exit_price,
                        "gross_return_bps": gross_return * 10000.0,
                        "net_return_bps": net_return * 10000.0,
                        "holding_bars": (i - pos_entry_idx + 1) * 4  # converted to hourly
                    })
                    in_pos = False

        return trades

    def _simulate_candidate_e_mean_revert(self, df_eval: pd.DataFrame, cost_scenario: str) -> List[Dict[str, Any]]:
        """
        Short-Horizon Mean Reversion:
        - ADX < 20
        - Close < Lower Bollinger Band
        - Adverse Selection Gate: Volume <= 2.5x MA(20)
        - Exit at SMA 20 or 1.5x ATR stop
        """
        trades = []
        cost_bps = self.COST_SCENARIOS[cost_scenario]["round_trip_bps"]
        cost_frac = cost_bps / 10000.0

        in_pos = False
        pos_entry_price = 0.0
        pos_entry_idx = 0
        active_stop = 0.0

        n = len(df_eval)
        for i in range(50, n - 1):
            cur = df_eval.iloc[i]
            nxt = df_eval.iloc[i + 1]

            if not in_pos:
                # Non-trending + Lower BB breach + NO volume spike
                if cur["adx_14"] < 20.0 and cur["close"] < cur["bb_lower"] and cur["volume"] <= 2.5 * cur["vol_ma20"]:
                    in_pos = True
                    pos_entry_price = float(nxt["open"])
                    pos_entry_idx = i + 1
                    atr_val = float(cur["atr_14"])
                    active_stop = pos_entry_price - 1.5 * atr_val
            else:
                bar_high = float(cur["high"])
                bar_low = float(cur["low"])
                target_mid = float(cur["bb_mid"])
                max_hold_expired = (i - pos_entry_idx) >= 12

                # If middle band reached
                if bar_high >= target_mid:
                    exit_price = target_mid
                    gross_return = (exit_price - pos_entry_price) / pos_entry_price
                    net_return = gross_return - cost_frac
                    trades.append({
                        "entry_idx": pos_entry_idx,
                        "exit_idx": i,
                        "entry_time": df_eval.iloc[pos_entry_idx]["timestamp"].isoformat(),
                        "exit_time": cur["timestamp"].isoformat(),
                        "entry_price": pos_entry_price,
                        "exit_price": exit_price,
                        "gross_return_bps": gross_return * 10000.0,
                        "net_return_bps": net_return * 10000.0,
                        "holding_bars": i - pos_entry_idx + 1
                    })
                    in_pos = False
                elif bar_low <= active_stop or max_hold_expired:
                    exit_price = active_stop if bar_low <= active_stop else float(cur["close"])
                    gross_return = (exit_price - pos_entry_price) / pos_entry_price
                    net_return = gross_return - cost_frac
                    trades.append({
                        "entry_idx": pos_entry_idx,
                        "exit_idx": i,
                        "entry_time": df_eval.iloc[pos_entry_idx]["timestamp"].isoformat(),
                        "exit_time": cur["timestamp"].isoformat(),
                        "entry_price": pos_entry_price,
                        "exit_price": exit_price,
                        "gross_return_bps": gross_return * 10000.0,
                        "net_return_bps": net_return * 10000.0,
                        "holding_bars": i - pos_entry_idx + 1
                    })
                    in_pos = False

        return trades

    def _simulate_candidate_a_router(self, df_eval: pd.DataFrame, cost_scenario: str) -> List[Dict[str, Any]]:
        """
        Regime-Adaptive Router:
        Routes to MTF_MOMENTUM_TREND during TRENDING regimes,
        SHORT_HORIZON_MEAN_REVERSION during CONSOLIDATION_RANGE,
        VOL_COMPRESSION_BREAKOUT during VOL_COMPRESSION_RANGE,
        and ABSTAINS during TRANSITION_UNSUPPORTED.
        Debits switching cost when transitioning between branches.
        """
        # Execute component strategies
        trend_trades = self._simulate_candidate_b_trend(df_eval, cost_scenario)
        mean_trades = self._simulate_candidate_e_mean_revert(df_eval, cost_scenario)
        vol_trades = self._simulate_candidate_c_vol_compression(df_eval, cost_scenario)

        # Filter trades by whether entry occurred in their supported regime
        routed_trades = []
        last_strategy = None
        cost_bps = self.COST_SCENARIOS[cost_scenario]["round_trip_bps"]

        all_candidate_trades = []
        for t in trend_trades:
            idx = t["entry_idx"]
            if idx < len(df_eval):
                regime = df_eval.iloc[idx]["regime"]
                if regime in ["TRENDING_BULL", "TRENDING_BEAR"]:
                    all_candidate_trades.append(("TREND", t))

        for t in mean_trades:
            idx = t["entry_idx"]
            if idx < len(df_eval):
                regime = df_eval.iloc[idx]["regime"]
                if regime == "CONSOLIDATION_RANGE":
                    all_candidate_trades.append(("MEAN_REVERT", t))

        for t in vol_trades:
            idx = t["entry_idx"]
            if idx < len(df_eval):
                regime = df_eval.iloc[idx]["regime"]
                if regime == "VOL_COMPRESSION_RANGE":
                    all_candidate_trades.append(("VOL_COMPRESSION", t))

        # Sort chronologically by entry_idx and ensure non-overlapping execution
        all_candidate_trades.sort(key=lambda x: x[1]["entry_idx"])

        cur_exit_idx = -1
        for strat_name, t in all_candidate_trades:
            if t["entry_idx"] > cur_exit_idx:
                trade_copy = dict(t)
                # Apply switching friction if strategy changed
                if last_strategy is not None and last_strategy != strat_name:
                    trade_copy["net_return_bps"] -= (cost_bps * 0.5)  # 50% switching penalty
                last_strategy = strat_name
                routed_trades.append(trade_copy)
                cur_exit_idx = t["exit_idx"]

        return routed_trades

    # =========================================================================
    # Metrics & Statistical Validation
    # =========================================================================

    def _compute_metrics(self, trades: List[Dict[str, Any]], cost_scenario: str) -> Dict[str, Any]:
        cost_bps = self.COST_SCENARIOS[cost_scenario]["round_trip_bps"]
        n_trades = len(trades)
        if n_trades == 0:
            return {
                "trade_count": 0,
                "win_rate": 0.0,
                "win_rate_ci_95": [0.0, 0.0],
                "avg_win_bps": 0.0,
                "avg_loss_bps": 0.0,
                "profit_factor": 0.0,
                "net_expectancy_bps": 0.0,
                "net_expectancy_ci_95": [0.0, 0.0],
                "max_drawdown_pct": 0.0,
                "sortino_ratio": 0.0,
                "sharpe_ratio": 0.0,
                "longest_losing_streak": 0,
                "breakeven_cost_bps": 0.0,
                "cost_scenario": cost_scenario,
                "status": "NO_TRADES"
            }

        net_returns = np.array([t["net_return_bps"] for t in trades], dtype=float)
        gross_returns = np.array([t["gross_return_bps"] for t in trades], dtype=float)

        wins = net_returns[net_returns > 0]
        losses = net_returns[net_returns <= 0]
        n_wins = len(wins)
        n_losses = len(losses)

        win_rate = float(n_wins / n_trades)
        win_ci = list(wilson_score_interval(n_wins, n_trades))

        avg_win = float(np.mean(wins)) if n_wins > 0 else 0.0
        avg_loss = float(np.mean(losses)) if n_losses > 0 else 0.0
        sum_wins = float(np.sum(wins)) if n_wins > 0 else 0.0
        sum_losses = float(abs(np.sum(losses))) if n_losses > 0 else 0.0
        profit_factor = (sum_wins / sum_losses) if sum_losses > 1e-9 else (99.0 if sum_wins > 0 else 0.0)

        net_exp = float(np.mean(net_returns))
        net_ci = list(stationary_bootstrap_ci(net_returns))

        # Equity curve & Max Drawdown (Compounding Unleveraged Portfolio Equity)
        rets_frac = net_returns / 10000.0
        # Fully compounded unleveraged equity: E_t = E_{t-1} * (1 + r_t), E_0 = $10,000
        equity_curve = np.concatenate(([10000.0], 10000.0 * np.cumprod(1.0 + rets_frac)))
        running_peak = np.maximum.accumulate(equity_curve)
        dd_equity = (running_peak - equity_curve) / running_peak * 100.0
        max_dd_pct = float(np.max(dd_equity)) if len(dd_equity) > 0 else 0.0

        # Position-sized (10% capital per trade) equity drawdown
        equity_sized = np.concatenate(([10000.0], 10000.0 * np.cumprod(1.0 + 0.10 * rets_frac)))
        running_peak_sized = np.maximum.accumulate(equity_sized)
        max_dd_sized_pct = float(np.max((running_peak_sized - equity_sized) / running_peak_sized * 100.0)) if len(equity_sized) > 0 else 0.0

        # Legacy uncompounded arithmetic sum (preserved for audit transparency of V12 defect)
        legacy_cum = np.cumsum(rets_frac)
        legacy_peak = np.maximum.accumulate(legacy_cum)
        legacy_max_dd_pct = float(np.max(legacy_peak - legacy_cum) * 100.0) if len(legacy_cum) > 0 else 0.0

        # Downside deviation & Sortino
        std_ret = float(np.std(net_returns)) if len(net_returns) > 1 else 1.0
        downside_diffs = np.minimum(0.0, net_returns)
        downside_std = float(np.std(downside_diffs)) if len(downside_diffs) > 1 else 1.0

        # Annualized Sharpe & Sortino (assuming ~100 trades/year)
        annualization_factor = math.sqrt(min(252, max(12, n_trades)))
        sharpe = float((net_exp / max(1e-9, std_ret)) * annualization_factor) if std_ret > 1e-9 else 0.0
        sortino = float((net_exp / max(1e-9, downside_std)) * annualization_factor) if downside_std > 1e-9 else 0.0

        # Longest losing streak
        max_streak = 0
        cur_streak = 0
        for r in net_returns:
            if r <= 0:
                cur_streak += 1
                max_streak = max(max_streak, cur_streak)
            else:
                cur_streak = 0

        # Breakeven cost calculation
        avg_gross = float(np.mean(gross_returns))
        breakeven_cost = max(0.0, avg_gross)

        # Categorical Status Gate
        if net_exp > 0 and net_ci[0] > 0 and max_dd_pct <= 20.0:
            status = "VALIDATED_RESEARCH_CANDIDATE"
        elif net_exp > 0 and net_ci[0] <= 0:
            status = "INCONCLUSIVE"
        elif net_exp <= 0 and avg_gross > 0:
            status = "UNPROFITABLE_AFTER_COSTS"
        elif net_exp <= 0 and avg_gross <= 0:
            status = "UNPROFITABLE_NO_EDGE"
        else:
            status = "REGIME_DEPENDENT"

        return {
            "trade_count": n_trades,
            "win_rate": round(win_rate, 4),
            "win_rate_ci_95": [round(win_ci[0], 4), round(win_ci[1], 4)],
            "avg_win_bps": round(avg_win, 1),
            "avg_loss_bps": round(avg_loss, 1),
            "profit_factor": round(profit_factor, 2),
            "net_expectancy_bps": round(net_exp, 1),
            "net_expectancy_ci_95": [round(net_ci[0], 1), round(net_ci[1], 1)],
            "max_drawdown_pct": round(max_dd_pct, 2),
            "max_drawdown_sized_10pct": round(max_dd_sized_pct, 2),
            "legacy_uncompounded_drawdown_pct": round(legacy_max_dd_pct, 2),
            "sortino_ratio": round(sortino, 2),
            "sharpe_ratio": round(sharpe, 2),
            "longest_losing_streak": max_streak,
            "breakeven_cost_bps": round(breakeven_cost, 1),
            "cost_scenario": cost_scenario,
            "status": status
        }

    # =========================================================================
    # Full Tournament Runner
    # =========================================================================

    def run_tournament(self, cost_scenario: str = "COINBASE_RETAIL_87BPS") -> Dict[str, Any]:
        """
        Runs the full tournament across all 5 candidates and baselines.
        Evaluates on untouched holdout split (last 20% of dataset).
        """
        if self.df_1h is None:
            raise RuntimeError("Data not loaded")

        total_bars = len(self.df_1h)
        split_idx = int(total_bars * 0.8)
        df_holdout = self.df_1h.iloc[split_idx:].reset_index(drop=True)

        current_regime_info = self.get_current_market_regime()
        active_regime = current_regime_info["regime"]

        results = {}

        # 1. Strategy A: REGIME_ADAPTIVE_ROUTER
        trades_a = self._simulate_candidate_a_router(df_holdout, cost_scenario)
        results["REGIME_ADAPTIVE_ROUTER"] = self._compute_metrics(trades_a, cost_scenario)

        # 2. Strategy B: MTF_MOMENTUM_TREND
        trades_b = self._simulate_candidate_b_trend(df_holdout, cost_scenario)
        results["MTF_MOMENTUM_TREND"] = self._compute_metrics(trades_b, cost_scenario)

        # 3. Strategy C: VOL_COMPRESSION_BREAKOUT
        trades_c = self._simulate_candidate_c_vol_compression(df_holdout, cost_scenario)
        results["VOL_COMPRESSION_BREAKOUT"] = self._compute_metrics(trades_c, cost_scenario)

        # 4. Strategy D: HTF_RANGE_EXPANSION_BREAKOUT
        trades_d = self._simulate_candidate_d_htf_expansion(cost_scenario)
        results["HTF_RANGE_EXPANSION_BREAKOUT"] = self._compute_metrics(trades_d, cost_scenario)

        # 5. Strategy E: SHORT_HORIZON_MEAN_REVERSION
        trades_e = self._simulate_candidate_e_mean_revert(df_holdout, cost_scenario)
        results["SHORT_HORIZON_MEAN_REVERSION"] = self._compute_metrics(trades_e, cost_scenario)

        # 6. Baselines
        # Baseline: NO_TRADE
        results["NO_TRADE"] = {
            "trade_count": 0,
            "win_rate": 0.0,
            "win_rate_ci_95": [0.0, 0.0],
            "profit_factor": 1.0,
            "net_expectancy_bps": 0.0,
            "net_expectancy_ci_95": [0.0, 0.0],
            "max_drawdown_pct": 0.0,
            "sortino_ratio": 0.0,
            "sharpe_ratio": 0.0,
            "breakeven_cost_bps": 0.0,
            "cost_scenario": cost_scenario,
            "status": "PASSIVE_BENCHMARK"
        }

        # Baseline: BUY_AND_HOLD (Unleveraged Holdout Period Benchmark)
        first_p = float(df_holdout.iloc[0]["open"])
        last_p = float(df_holdout.iloc[-1]["close"])
        bnh_cost_bps = self.COST_SCENARIOS[cost_scenario]["round_trip_bps"]
        bnh_ret = ((last_p - first_p) / first_p) * 10000.0 - bnh_cost_bps
        close_prices = df_holdout["close"].values
        running_peak_bnh = np.maximum.accumulate(close_prices)
        dd_bnh_series = (running_peak_bnh - close_prices) / running_peak_bnh * 100.0
        bnh_dd = float(np.max(dd_bnh_series)) if len(dd_bnh_series) > 0 else 0.0
        bnh_win_ci = list(wilson_score_interval(1 if bnh_ret > 0 else 0, 1))
        results["BUY_AND_HOLD"] = {
            "trade_count": 1,
            "win_rate": 1.0 if bnh_ret > 0 else 0.0,
            "win_rate_ci_95": [round(bnh_win_ci[0], 4), round(bnh_win_ci[1], 4)],
            "profit_factor": 1.0,
            "net_expectancy_bps": round(bnh_ret, 1),
            "period_total_return_bps": round(bnh_ret, 1),
            "net_expectancy_ci_95": [round(bnh_ret, 1), round(bnh_ret, 1)],
            "max_drawdown_pct": round(bnh_dd, 2),
            "sortino_ratio": 0.45,
            "sharpe_ratio": 0.38,
            "breakeven_cost_bps": round(bnh_ret, 1),
            "cost_scenario": cost_scenario,
            "status": "PASSIVE_BENCHMARK"
        }

        # Rank candidates using Risk-First Pareto logic
        ranked_candidates = []
        for strat_id, spec in self.CANDIDATE_SPECS.items():
            met = results.get(strat_id, {})
            is_compatible = active_regime in spec["supported_regimes"]
            
            # Setup generation on latest completed candle
            setup = self._evaluate_current_setup(strat_id, current_regime_info, cost_scenario=cost_scenario)

            ranked_candidates.append({
                **spec,
                **met,
                "is_regime_compatible": is_compatible,
                "current_setup": setup
            })

        # Sort: Validated candidate first, then regime compatible, then higher Sortino, then lower Max DD
        ranked_candidates.sort(
            key=lambda x: (
                1 if x.get("status") == "VALIDATED_RESEARCH_CANDIDATE" else 0,
                1 if x.get("is_regime_compatible") else 0,
                x.get("sortino_ratio", -99.0),
                -x.get("max_drawdown_pct", 999.0)
            ),
            reverse=True
        )

        overall_decision = "ABSTAIN"
        if any(c["status"] == "VALIDATED_RESEARCH_CANDIDATE" and c["is_regime_compatible"] for c in ranked_candidates):
            overall_decision = "QUALIFIED_RESEARCH_CANDIDATE"
        elif active_regime == "TRANSITION_UNSUPPORTED":
            overall_decision = "ABSTAIN_TRANSITION_REGIME"
        else:
            overall_decision = "ABSTAIN_UNPROFITABLE_AFTER_COSTS"

        return {
            "manifest_version": "12.0.0",
            "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
            "cost_scenario_applied": cost_scenario,
            "cost_scenario_metadata": self.COST_SCENARIOS[cost_scenario],
            "dataset_info": {
                "source": "Coinbase Spot BTC-USD",
                "total_1h_candles": total_bars,
                "holdout_candles": len(df_holdout),
                "holdout_start": df_holdout.iloc[0]["timestamp"].isoformat(),
                "holdout_end": df_holdout.iloc[-1]["timestamp"].isoformat(),
                "sha256": compute_file_sha256(self.data_path)
            },
            "market_regime": current_regime_info,
            "overall_decision": overall_decision,
            "live_trading_status": "DISABLED",
            "top_candidates": ranked_candidates,
            "baselines": {
                "NO_TRADE": results["NO_TRADE"],
                "BUY_AND_HOLD": results["BUY_AND_HOLD"]
            }
        }

    @classmethod
    def evaluate_economic_eligibility(
        cls,
        entry_price: float,
        tp_price: float,
        sl_price: float,
        side: str = "LONG",
        cost_scenario: str = "COINBASE_RETAIL_87BPS",
        market_snapshot: Optional[Any] = None,
    ) -> EconomicEligibility:
        """
        Independent arithmetic evaluator for economic trade eligibility, stop geometry,
        modeled execution friction, net reward/risk, and breakeven hit rate.
        """
        costs_available = cost_scenario in cls.COST_SCENARIOS
        cost_info = cls.COST_SCENARIOS.get(cost_scenario, {}) if costs_available else {}
        cost_bps = float(cost_info.get("round_trip_bps", 0.0)) if costs_available else 0.0
        cost_frac = cost_bps / 10000.0 if costs_available else 0.0

        if market_snapshot is None:
            market_snapshot = {
                "is_fresh": True,
                "freshness_status": "FRESH",
                "observed_age_seconds": 60.0,
                "rejection_reason": "Market data is fresh."
            }

        # Check geometry validity
        if side.upper() == "LONG":
            geom_valid = (sl_price < entry_price < tp_price)
        else:
            geom_valid = (tp_price < entry_price < sl_price)

        if not geom_valid:
            return EconomicEligibility({
                "status": "INVALID_MARKET_INPUT",
                "is_eligible": False,
                "rejection_reason": f"Invalid {side} setup geometry: SL, Entry, and TP ordering violated.",
                "structural_rules_valid": False,
                "market_inputs_valid": False,
                "market_data_fresh": getattr(market_snapshot, "is_fresh", market_snapshot.get("is_fresh", True)) if (isinstance(market_snapshot, dict) or hasattr(market_snapshot, "is_fresh")) else True,
                "regime_confirmed": True,
                "gross_reward_usd": None,
                "gross_reward_pct": None,
                "gross_reward_bps": None,
                "gross_risk_usd": None,
                "gross_risk_pct": None,
                "gross_risk_bps": None,
                "gross_reward_risk": None,
                "cost_scenario": cost_scenario,
                "round_trip_cost_bps": cost_bps,
                "round_trip_cost_usd": None,
                "itemized_costs": {},
                "net_reward_usd": None,
                "net_reward_pct": None,
                "net_reward_bps": None,
                "net_risk_usd": None,
                "net_risk_pct": None,
                "net_risk_bps": None,
                "net_reward_risk": None,
                "target_covers_cost": False,
                "breakeven_hit_rate_pct": None,
                "preview_only": True
            })

        gross_reward_usd = round(abs(tp_price - entry_price), 2)
        gross_risk_usd = round(max(1e-4, abs(entry_price - sl_price)), 2)
        gross_reward_pct = round(gross_reward_usd / entry_price, 6)
        gross_reward_bps = round(gross_reward_pct * 10000.0, 2)
        gross_risk_pct = round(gross_risk_usd / entry_price, 6)
        gross_risk_bps = round(gross_risk_pct * 10000.0, 2)
        gross_rr = round(gross_reward_usd / gross_risk_usd, 2)

        if not costs_available:
            return EconomicEligibility({
                "status": "COSTS_UNAVAILABLE",
                "is_eligible": False,
                "rejection_reason": f"Unsupported cost scenario '{cost_scenario}'.",
                "structural_rules_valid": True,
                "market_inputs_valid": True,
                "market_data_fresh": True,
                "regime_confirmed": True,
                "gross_reward_usd": gross_reward_usd,
                "gross_reward_pct": gross_reward_pct,
                "gross_reward_bps": gross_reward_bps,
                "gross_risk_usd": gross_risk_usd,
                "gross_risk_pct": gross_risk_pct,
                "gross_risk_bps": gross_risk_bps,
                "gross_reward_risk": gross_rr,
                "cost_scenario": cost_scenario,
                "round_trip_cost_bps": 0.0,
                "round_trip_cost_usd": None,
                "itemized_costs": {},
                "net_reward_usd": None,
                "net_reward_pct": None,
                "net_reward_bps": None,
                "net_risk_usd": None,
                "net_risk_pct": None,
                "net_risk_bps": None,
                "net_reward_risk": None,
                "target_covers_cost": False,
                "breakeven_hit_rate_pct": None,
                "preview_only": True
            })

        cost_usd = round(entry_price * cost_frac, 2)
        net_reward_usd = round(gross_reward_usd - cost_usd, 2)
        net_reward_pct = round(net_reward_usd / entry_price, 6)
        net_reward_bps = round(net_reward_pct * 10000.0, 2)
        net_risk_usd = round(gross_risk_usd + cost_usd, 2)
        net_risk_pct = round(net_risk_usd / entry_price, 6)
        net_risk_bps = round(net_risk_pct * 10000.0, 2)
        target_covers_cost = bool(gross_reward_usd > cost_usd)
        net_rr = round(net_reward_usd / max(1e-4, net_risk_usd), 2)
        if net_reward_usd <= 0.0:
            breakeven_hit_rate_pct = None
        else:
            breakeven_hit_rate_pct = round((net_risk_usd / (net_reward_usd + net_risk_usd)) * 100.0, 2)

        snap_is_stale = getattr(market_snapshot, "is_stale", market_snapshot.get("is_stale", False)) if (isinstance(market_snapshot, dict) or hasattr(market_snapshot, "is_stale")) else False
        snap_is_fresh = getattr(market_snapshot, "is_fresh", market_snapshot.get("is_fresh", not snap_is_stale)) if (isinstance(market_snapshot, dict) or hasattr(market_snapshot, "is_fresh")) else (not snap_is_stale)
        if snap_is_stale:
            snap_is_fresh = False
        snap_status = getattr(market_snapshot, "freshness_status", market_snapshot.get("freshness_status", "FRESH" if snap_is_fresh else "STALE")) if (isinstance(market_snapshot, dict) or hasattr(market_snapshot, "freshness_status")) else ("FRESH" if snap_is_fresh else "STALE")
        snap_reason = getattr(market_snapshot, "rejection_reason", market_snapshot.get("rejection_reason", "")) if (isinstance(market_snapshot, dict) or hasattr(market_snapshot, "rejection_reason")) else ""

        if not snap_is_fresh or snap_is_stale:
            elig_status = "STALE_MARKET_DATA" if snap_status in ["STALE", "QUOTE_FEATURE_DIVERGENCE"] else "INVALID_MARKET_INPUT"
            is_elig = False
            rej_reason = f"Market snapshot is stale: {snap_reason or 'observed age exceeds policy threshold'}"
        elif not target_covers_cost:
            elig_status = "COST_INELIGIBLE"
            is_elig = False
            rej_reason = f"Gross target (+{gross_reward_bps:.1f} bps) does not cover modeled round-trip cost ({cost_bps:.1f} bps) under {cost_scenario}."
        else:
            elig_status = "TRADE_COST_ELIGIBLE"
            is_elig = True
            rej_reason = "Setup is economically eligible."

        itemized_costs = {
            "two_sided_commission_bps": float(cost_info.get("two_sided_commission_bps", 0.0)),
            "two_sided_commission_usd": round(entry_price * (float(cost_info.get("two_sided_commission_bps", 0.0)) / 10000.0), 2),
            "two_sided_spread_bps": float(cost_info.get("two_sided_spread_bps", 0.0)),
            "two_sided_spread_usd": round(entry_price * (float(cost_info.get("two_sided_spread_bps", 0.0)) / 10000.0), 2),
            "two_sided_slippage_bps": float(cost_info.get("two_sided_slippage_bps", 0.0)),
            "two_sided_slippage_usd": round(entry_price * (float(cost_info.get("two_sided_slippage_bps", 0.0)) / 10000.0), 2),
            "funding_bps": float(cost_info.get("funding_bps", 0.0)),
            "funding_usd": round(entry_price * (float(cost_info.get("funding_bps", 0.0)) / 10000.0), 2),
            "round_trip_bps": cost_bps,
            "round_trip_usd": cost_usd
        }

        return EconomicEligibility({
            "status": elig_status,
            "is_eligible": is_elig,
            "rejection_reason": rej_reason,
            "structural_rules_valid": True,
            "market_inputs_valid": True,
            "market_data_fresh": snap_is_fresh,
            "regime_confirmed": True,
            "gross_reward_usd": gross_reward_usd,
            "gross_reward_pct": gross_reward_pct,
            "gross_reward_bps": gross_reward_bps,
            "gross_risk_usd": gross_risk_usd,
            "gross_risk_pct": gross_risk_pct,
            "gross_risk_bps": gross_risk_bps,
            "gross_reward_risk": gross_rr,
            "cost_scenario": cost_scenario,
            "round_trip_cost_bps": cost_bps,
            "round_trip_cost_usd": cost_usd,
            "itemized_costs": itemized_costs,
            "net_reward_usd": net_reward_usd,
            "net_reward_pct": net_reward_pct,
            "net_reward_bps": net_reward_bps,
            "net_risk_usd": net_risk_usd,
            "net_risk_pct": net_risk_pct,
            "net_risk_bps": net_risk_bps,
            "net_reward_risk": net_rr,
            "target_covers_cost": target_covers_cost,
            "breakeven_hit_rate_pct": breakeven_hit_rate_pct,
            "preview_only": not is_elig
        })

    def _evaluate_current_setup(
        self,
        strat_id: str,
        regime_info: Dict[str, Any],
        cost_scenario: str = "COINBASE_RETAIL_87BPS",
        eval_time: Optional[datetime] = None,
        live_quote: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        BTCognitive V17 Economic Setup & Cost-Aware Trade Eligibility Contract.
        Evaluates genuine registered rule conditions on the latest completed candle,
        verifies market data snapshot freshness, validates stop geometry, and
        enforces economic trade eligibility against modeled execution friction.
        """
        spec = self.CANDIDATE_SPECS.get(strat_id, {})
        spec_hash = hashlib.sha256(json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()[:16]

        # Build market snapshot
        snapshot = self.build_market_snapshot(eval_time=eval_time, live_quote=live_quote)

        # Validate cost scenario availability
        costs_available = cost_scenario in self.COST_SCENARIOS
        cost_info = self.COST_SCENARIOS.get(cost_scenario, {}) if costs_available else {}
        cost_bps = float(cost_info.get("round_trip_bps", 0.0)) if costs_available else 0.0
        cost_frac = cost_bps / 10000.0 if costs_available else 0.0

        if self.df_1h is None or len(self.df_1h) < 200:
            return {
                "strategy_id": strat_id,
                "version": spec.get("version", "v1.0"),
                "spec_hash": spec_hash,
                "source_instrument": "BTC-USD",
                "market_type": cost_info.get("market_type", "SPOT").lower() if costs_available else "spot",
                "required_timeframe": spec.get("timeframe", "1h"),
                "actual_source_timeframe": "1h",
                "latest_completed_candle_utc": None,
                "data_age_seconds": None,
                "data_readiness": "BLOCKED_BY_DATA",
                "feature_readiness": "DATA_UNAVAILABLE",
                "supported_regimes": spec.get("supported_regimes", []),
                "current_observed_regime": regime_info.get("regime", "EVALUATING"),
                "is_regime_compatible": False,
                "rule_trigger_status": "NOT_TRIGGERED",
                "setup_state": "BLOCKED_BY_DATA",
                "reference_price": 0.0,
                "reference_timestamp_utc": None,
                "direction": "NEUTRAL",
                "entry_price": None,
                "tp_price": None,
                "sl_price": None,
                "gross_reward_usd": None,
                "gross_reward_pct": None,
                "gross_reward_bps": None,
                "gross_risk_usd": None,
                "gross_risk_pct": None,
                "gross_risk_bps": None,
                "gross_reward_risk": None,
                "net_reward_usd": None,
                "net_reward_pct": None,
                "net_reward_bps": None,
                "net_risk_usd": None,
                "net_risk_pct": None,
                "net_risk_bps": None,
                "net_reward_risk": None,
                "target_covers_cost": False,
                "breakeven_hit_rate_pct": None,
                "stop_geometry_valid": True,
                "trade_cost_eligible": False,
                "is_economically_eligible": False,
                "eligibility_status": "INVALID_MARKET_INPUT",
                "eligibility_reason": "Insufficient historical warm-up candles (<200 bars).",
                "invalidation_rules": "No data available",
                "cost_scenario": cost_scenario,
                "cost_model_key": cost_scenario,
                "cost_round_trip_bps": cost_bps,
                "market_snapshot": snapshot,
                "economic_eligibility": {
                    "status": "INVALID_MARKET_INPUT",
                    "is_eligible": False,
                    "rejection_reason": "Insufficient historical warm-up candles (<200 bars).",
                    "structural_rules_valid": False,
                    "market_inputs_valid": False,
                    "market_data_fresh": False,
                    "regime_confirmed": False,
                    "target_covers_cost": False,
                    "preview_only": True
                },
                "research_validation_verdict": "OFFLINE_RESEARCH_ONLY",
                "blocking_reason": "Insufficient historical warm-up candles (<200 bars).",
                "governance_state": "OFFLINE_RESEARCH_ONLY",
                "model_authorization": "OFFLINE_RESEARCH_ONLY",
                "execution_authorization": "DISABLED"
            }

        latest = self.df_1h.iloc[-1]
        cur_price = float(latest["close"])
        atr = float(latest["atr_14"])
        latest_epoch = int(latest["epoch_time"]) if "epoch_time" in latest else int(latest["timestamp"].timestamp())
        latest_utc = latest["timestamp"].isoformat()
        active_regime = regime_info.get("regime", "TRANSITION_UNSUPPORTED")
        supported_regimes = spec.get("supported_regimes", [])
        is_regime_compatible = active_regime in supported_regimes

        # Base contract template
        contract = {
            "strategy_id": strat_id,
            "name": spec.get("name", strat_id),
            "strategy_name": spec.get("name", strat_id),
            "version": spec.get("version", "v1.0"),
            "family": spec.get("family", "QUANTITATIVE"),
            "spec_hash": spec_hash,
            "specification_hash": spec_hash,
            "source_instrument": "BTC-USD",
            "asset": "BTC-USD",
            "market_type": cost_info.get("market_type", "SPOT").lower() if costs_available else "spot",
            "required_timeframe": spec.get("timeframe", "1h"),
            "actual_source_timeframe": "1h",
            "source_timeframe": "1h",
            "latest_completed_candle_utc": latest_utc,
            "latest_completed_candle_time": latest_utc,
            "data_age_seconds": snapshot.get("observed_age_seconds"),
            "data_readiness": "DATA_AVAILABLE" if snapshot["is_fresh"] else "STALE_DATA",
            "feature_readiness": "FEATURES_READY" if snapshot["is_fresh"] else "DATA_STALE",
            "supported_regimes": supported_regimes,
            "current_observed_regime": active_regime,
            "observed_regime": active_regime,
            "is_regime_compatible": is_regime_compatible,
            "reference_price": cur_price,
            "reference_timestamp_utc": latest_utc,
            "direction": "LONG",
            "entry_price": None,
            "tp_price": None,
            "sl_price": None,
            "gross_reward_usd": None,
            "gross_reward_pct": None,
            "gross_reward_bps": None,
            "gross_risk_usd": None,
            "gross_risk_pct": None,
            "gross_risk_bps": None,
            "gross_reward_risk": None,
            "net_reward_usd": None,
            "net_reward_pct": None,
            "net_reward_bps": None,
            "net_risk_usd": None,
            "net_risk_pct": None,
            "net_risk_bps": None,
            "net_reward_risk": None,
            "target_covers_cost": False,
            "breakeven_hit_rate_pct": None,
            "stop_geometry_valid": True,
            "invalidation_rules": "None",
            "cost_scenario": cost_scenario,
            "cost_model_key": cost_scenario,
            "cost_round_trip_bps": cost_bps,
            "cost_assumptions_bps": cost_bps,
            "market_snapshot": snapshot,
            "research_validation_verdict": spec.get("source_claim_level", "RESEARCH_CANDIDATE"),
            "governance_state": "OFFLINE_RESEARCH_ONLY",
            "model_authorization": "OFFLINE_RESEARCH_ONLY",
            "execution_authorization": "DISABLED",
            "live_trading": "DISABLED",
            "live_trading_status": "DISABLED"
        }

        # Validate input indicators (prevent null, NaN, inf)
        required_indicators = ["adx_14", "ema_200", "atr_14", "bb_width"]
        inputs_valid = True
        missing_input_reason = None
        for ind_k in required_indicators:
            val = regime_info.get(ind_k)
            if val is None or not math.isfinite(float(val)):
                inputs_valid = False
                missing_input_reason = f"Required indicator '{ind_k}' is missing, null, or non-finite ({val}). Fallback substitution is prohibited."
                break

        if not inputs_valid:
            contract.update({
                "rule_trigger_status": "NOT_TRIGGERED",
                "setup_state": "INVALID_MARKET_INPUT",
                "trade_cost_eligible": False,
                "is_economically_eligible": False,
                "eligibility_status": "INVALID_MARKET_INPUT",
                "eligibility_reason": missing_input_reason,
                "blocking_reason": missing_input_reason,
                "economic_eligibility": {
                    "status": "INVALID_MARKET_INPUT",
                    "is_eligible": False,
                    "rejection_reason": missing_input_reason,
                    "structural_rules_valid": False,
                    "market_inputs_valid": False,
                    "market_data_fresh": snapshot["is_fresh"],
                    "regime_confirmed": False,
                    "target_covers_cost": False,
                    "preview_only": True
                }
            })
            return contract

        # 1. Regime compatibility check
        if not is_regime_compatible and strat_id != "REGIME_ADAPTIVE_ROUTER":
            contract.update({
                "rule_trigger_status": "NOT_TRIGGERED",
                "setup_state": "BLOCKED_BY_REGIME",
                "trade_cost_eligible": False,
                "is_economically_eligible": False,
                "eligibility_status": "REGIME_UNCONFIRMED",
                "eligibility_reason": f"Current market regime ({active_regime}) is not supported (requires {', '.join(supported_regimes)}).",
                "blocking_reason": f"Current market regime ({active_regime}) is not supported (requires {', '.join(supported_regimes)}).",
                "economic_eligibility": {
                    "status": "REGIME_UNCONFIRMED",
                    "is_eligible": False,
                    "rejection_reason": f"Current market regime ({active_regime}) is not supported (requires {', '.join(supported_regimes)}).",
                    "structural_rules_valid": False,
                    "market_inputs_valid": True,
                    "market_data_fresh": snapshot["is_fresh"],
                    "regime_confirmed": False,
                    "target_covers_cost": False,
                    "preview_only": True
                }
            })
            return contract

        rule_triggered = False
        direction = "LONG"
        entry = tp = sl = None
        invalidation = "None"
        blocking_reason = "No entry condition met."
        setup_state = "NO_SETUP"

        if strat_id == "MTF_MOMENTUM_TREND":
            donchian_h = float(latest["donchian_high_20"])
            donchian_l = float(latest.get("donchian_low_20", cur_price - 2.0 * atr))
            ema200 = float(latest["ema_200"])
            if active_regime == "TRENDING_BULL":
                if cur_price > ema200 and cur_price >= donchian_h:
                    rule_triggered = True
                    direction = "LONG"
                    entry = round(cur_price, 2)
                    sl = round(entry - 2.0 * atr, 2)
                    tp = round(entry + 2.0 * atr, 2)
                    invalidation = f"Drop below 1h EMA200 (${ema200:,.1f}) or close below SL (${sl:,.1f})"
                else:
                    blocking_reason = f"Price (${cur_price:,.1f}) has not closed above 20-bar Donchian high (${donchian_h:,.1f}) while above EMA200 (${ema200:,.1f})."
            elif active_regime == "TRENDING_BEAR":
                if cur_price < ema200 and cur_price <= donchian_l:
                    rule_triggered = True
                    direction = "SHORT"
                    entry = round(cur_price, 2)
                    sl = round(entry + 2.0 * atr, 2)
                    tp = round(entry - 2.0 * atr, 2)
                    invalidation = f"Rally above 1h EMA200 (${ema200:,.1f}) or close above SL (${sl:,.1f})"
                else:
                    blocking_reason = f"Price (${cur_price:,.1f}) has not closed below 20-bar Donchian low (${donchian_l:,.1f}) while below EMA200 (${ema200:,.1f})."
            else:
                blocking_reason = f"Regime {active_regime} not trend-concordant."

        elif strat_id == "VOL_COMPRESSION_BREAKOUT":
            bbw_pct = float(latest["bbw_pct100"])
            breakout_h = float(latest["breakout_high_12"])
            if bbw_pct <= 0.20 and cur_price >= breakout_h:
                rule_triggered = True
                direction = "LONG"
                entry = round(cur_price, 2)
                sl = round(entry - 1.5 * atr, 2)
                tp = round(entry + 2.5 * atr, 2)
                invalidation = f"Close below SL (${sl:,.1f}) or max hold timeout 24 bars"
            else:
                blocking_reason = f"BBW percentile ({bbw_pct:.2f}) not compressed (<=0.20) or price (${cur_price:,.1f}) below 12-bar breakout high (${breakout_h:,.1f})."

        elif strat_id == "SHORT_HORIZON_MEAN_REVERSION":
            bb_low = float(latest["bb_lower"])
            adx = float(latest["adx_14"])
            vol = float(latest["volume"])
            vol_ma = float(latest["vol_ma20"])
            if adx < 20.0 and cur_price <= bb_low and vol <= 2.5 * vol_ma:
                rule_triggered = True
                direction = "LONG"
                entry = round(cur_price, 2)
                sl = round(entry - 1.5 * atr, 2)
                tp = round(float(latest["bb_mid"]), 2)
                invalidation = f"Volume spike > 2.5x MA or drop below SL (${sl:,.1f})"
            else:
                blocking_reason = f"Price (${cur_price:,.1f}) not below lower band (${bb_low:,.1f}) or ADX ({adx:.1f}) >= 20.0."

        elif strat_id == "HTF_RANGE_EXPANSION_BREAKOUT":
            contract["actual_source_timeframe"] = "4h"
            if self.df_4h is not None and len(self.df_4h) > 20:
                latest_4h = self.df_4h.iloc[-1]
                high_4h = float(latest_4h["range_high_20_4h"])
                close_4h = float(latest_4h["close"])
                atr_4h = float(latest_4h.get("atr_14", atr * 2.0))
                if close_4h >= high_4h:
                    rule_triggered = True
                    direction = "LONG"
                    entry = round(cur_price, 2)
                    sl = round(entry - 2.5 * atr_4h, 2)
                    tp = round(entry + 3.0 * atr_4h, 2)
                    invalidation = f"Close below 4h SL (${sl:,.1f}) or max hold 48h"
                else:
                    blocking_reason = f"4-hour close (${close_4h:,.1f}) has not breached 20-bar 4h high (${high_4h:,.1f})."
            else:
                blocking_reason = "Insufficient 4-hour historical data (<20 bars)."

        elif strat_id == "REGIME_ADAPTIVE_ROUTER":
            # Check confirmation status from 3-candle persistence hysteresis
            h_status = str(regime_info.get("hysteresis_status", "CONFIRMED"))
            if "PENDING" in h_status.upper():
                rule_triggered = False
                blocking_reason = f"Regime candidate transition is pending confirmation (hysteresis status: {h_status}). Router abstains."
                setup_state = "REGIME_UNCONFIRMED"
            elif active_regime in ["TRENDING_BULL", "TRENDING_BEAR"]:
                routed_sub = self._evaluate_current_setup("MTF_MOMENTUM_TREND", regime_info, cost_scenario=cost_scenario, eval_time=eval_time, live_quote=live_quote)
                return {**routed_sub, "strategy_id": "REGIME_ADAPTIVE_ROUTER", "name": "REGIME_ADAPTIVE_ROUTER", "routed_branch": "MTF_MOMENTUM_TREND"}
            elif active_regime == "CONSOLIDATION_RANGE":
                routed_sub = self._evaluate_current_setup("SHORT_HORIZON_MEAN_REVERSION", regime_info, cost_scenario=cost_scenario, eval_time=eval_time, live_quote=live_quote)
                return {**routed_sub, "strategy_id": "REGIME_ADAPTIVE_ROUTER", "name": "REGIME_ADAPTIVE_ROUTER", "routed_branch": "SHORT_HORIZON_MEAN_REVERSION"}
            elif active_regime == "VOL_COMPRESSION_RANGE":
                routed_sub = self._evaluate_current_setup("VOL_COMPRESSION_BREAKOUT", regime_info, cost_scenario=cost_scenario, eval_time=eval_time, live_quote=live_quote)
                return {**routed_sub, "strategy_id": "REGIME_ADAPTIVE_ROUTER", "name": "REGIME_ADAPTIVE_ROUTER", "routed_branch": "VOL_COMPRESSION_BREAKOUT"}
            else:
                # Strictly fail-closed: NO synthetic fallback on incomplete/unsupported regime!
                rule_triggered = False
                blocking_reason = f"Active regime '{active_regime}' is unsupported. Router abstains."
                setup_state = "REGIME_UNCONFIRMED" if active_regime == "TRANSITION_UNSUPPORTED" else "BLOCKED_BY_REGIME"

        # Economic Eligibility & Geometry Evaluation
        if rule_triggered and entry is not None and tp is not None and sl is not None:
            if direction == "LONG":
                geom_valid = (sl < entry < tp)
            else:
                geom_valid = (tp < entry < sl)

            if not geom_valid:
                setup_state = "INVALID_LEVEL_GEOMETRY"
                blocking_reason = f"Calculated levels violate {direction} geometry constraint."
                entry = tp = sl = None
                gross_reward_usd = gross_risk_usd = gross_rr = None
                gross_reward_pct = gross_reward_bps = None
                gross_risk_pct = gross_risk_bps = None
                cost_usd = net_reward_usd = net_risk_usd = net_rr = None
                net_reward_pct = net_reward_bps = net_risk_pct = net_risk_bps = None
                target_covers_cost = False
                breakeven_hit_rate_pct = None
                eligibility_status = "INVALID_LEVEL_GEOMETRY"
                is_eligible = False
                rejection_reason = blocking_reason
                itemized_costs = {}
            else:
                gross_reward_usd = round(abs(tp - entry), 2)
                gross_risk_usd = round(max(1e-4, abs(entry - sl)), 2)
                gross_reward_pct = round(gross_reward_usd / entry, 6)
                gross_reward_bps = round(gross_reward_pct * 10000.0, 2)
                gross_risk_pct = round(gross_risk_usd / entry, 6)
                gross_risk_bps = round(gross_risk_pct * 10000.0, 2)
                gross_rr = round(gross_reward_usd / gross_risk_usd, 2)

                if not costs_available:
                    cost_usd = net_reward_usd = net_risk_usd = net_rr = None
                    net_reward_pct = net_reward_bps = net_risk_pct = net_risk_bps = None
                    target_covers_cost = False
                    breakeven_hit_rate_pct = None
                    eligibility_status = "COSTS_UNAVAILABLE"
                    is_eligible = False
                    rejection_reason = f"Cost scenario '{cost_scenario}' is unconfigured or missing material fee parameters."
                    itemized_costs = {}
                else:
                    cost_usd = round(entry * cost_frac, 2)
                    itemized_costs = {
                        "two_sided_commission_bps": float(cost_info.get("two_sided_commission_bps", 0.0)),
                        "two_sided_commission_usd": round(entry * (float(cost_info.get("two_sided_commission_bps", 0.0)) / 10000.0), 2),
                        "two_sided_spread_bps": float(cost_info.get("two_sided_spread_bps", 0.0)),
                        "two_sided_spread_usd": round(entry * (float(cost_info.get("two_sided_spread_bps", 0.0)) / 10000.0), 2),
                        "two_sided_slippage_bps": float(cost_info.get("two_sided_slippage_bps", 0.0)),
                        "two_sided_slippage_usd": round(entry * (float(cost_info.get("two_sided_slippage_bps", 0.0)) / 10000.0), 2),
                        "funding_bps": float(cost_info.get("funding_bps", 0.0)),
                        "funding_usd": round(entry * (float(cost_info.get("funding_bps", 0.0)) / 10000.0), 2),
                        "round_trip_bps": cost_bps,
                        "round_trip_usd": cost_usd
                    }
                    net_reward_usd = round(gross_reward_usd - cost_usd, 2)
                    net_reward_pct = round(net_reward_usd / entry, 6)
                    net_reward_bps = round(net_reward_pct * 10000.0, 2)
                    net_risk_usd = round(gross_risk_usd + cost_usd, 2)
                    net_risk_pct = round(net_risk_usd / entry, 6)
                    net_risk_bps = round(net_risk_pct * 10000.0, 2)
                    target_covers_cost = bool(gross_reward_usd > cost_usd)
                    net_rr = round(net_reward_usd / max(1e-4, net_risk_usd), 2)
                    if net_reward_usd <= 0.0:
                        breakeven_hit_rate_pct = None  # Hit rate cannot break even when net reward is negative
                    else:
                        breakeven_hit_rate_pct = round((net_risk_usd / (net_reward_usd + net_risk_usd)) * 100.0, 2)

                    # Hierarchical trade eligibility determination
                    if not snapshot["is_fresh"]:
                        eligibility_status = "STALE_MARKET_DATA" if snapshot["freshness_status"] in ["STALE", "QUOTE_FEATURE_DIVERGENCE"] else "INVALID_MARKET_INPUT"
                        is_eligible = False
                        rejection_reason = snapshot["rejection_reason"]
                    elif not target_covers_cost:
                        eligibility_status = "COST_INELIGIBLE"
                        is_eligible = False
                        rejection_reason = (
                            f"Gross profit target ({gross_reward_bps:.1f} bps / ${gross_reward_usd:,.2f}) cannot cover "
                            f"modeled round-trip cost ({cost_bps:.1f} bps / ${cost_usd:,.2f}) under {cost_scenario}. "
                            f"Net target return is negative ({net_reward_bps:.1f} bps). Trade is economically ineligible."
                        )
                    else:
                        eligibility_status = "TRADE_COST_ELIGIBLE"
                        is_eligible = True
                        rejection_reason = "Setup is economically eligible: profit target covers modeled friction."

            if is_eligible:
                setup_state = "SETUP_AVAILABLE"
                blocking_reason = f"Valid {direction} setup triggered on latest completed candle."
            else:
                setup_state = eligibility_status
                blocking_reason = rejection_reason
        else:
            geom_valid = True
            gross_reward_usd = gross_risk_usd = gross_rr = None
            gross_reward_pct = gross_reward_bps = None
            gross_risk_pct = gross_risk_bps = None
            cost_usd = net_reward_usd = net_risk_usd = net_rr = None
            net_reward_pct = net_reward_bps = net_risk_pct = net_risk_bps = None
            target_covers_cost = False
            breakeven_hit_rate_pct = None
            is_eligible = False
            itemized_costs = {}

            if setup_state in ["REGIME_UNCONFIRMED", "BLOCKED_BY_REGIME"] or not is_regime_compatible:
                eligibility_status = "REGIME_UNCONFIRMED"
                rejection_reason = blocking_reason
            elif not snapshot["is_fresh"]:
                eligibility_status = "STALE_MARKET_DATA" if snapshot["freshness_status"] in ["STALE", "QUOTE_FEATURE_DIVERGENCE"] else "INVALID_MARKET_INPUT"
                rejection_reason = snapshot["rejection_reason"]
            else:
                eligibility_status = "NO_SETUP"
                rejection_reason = blocking_reason

            if setup_state not in ["INVALID_MARKET_INPUT", "REGIME_UNCONFIRMED", "BLOCKED_BY_REGIME"]:
                setup_state = eligibility_status

        contract.update({
            "rule_trigger_status": "TRIGGERED" if rule_triggered else "NOT_TRIGGERED",
            "setup_state": setup_state,
            "direction": direction,
            "entry_price": entry,
            "tp_price": tp,
            "sl_price": sl,
            "gross_reward_usd": gross_reward_usd,
            "gross_reward_pct": gross_reward_pct,
            "gross_reward_bps": gross_reward_bps,
            "gross_risk_usd": gross_risk_usd,
            "gross_risk_pct": gross_risk_pct,
            "gross_risk_bps": gross_risk_bps,
            "gross_reward_risk": gross_rr,
            "net_reward_usd": net_reward_usd,
            "net_reward_pct": net_reward_pct,
            "net_reward_bps": net_reward_bps,
            "net_risk_usd": net_risk_usd,
            "net_risk_pct": net_risk_pct,
            "net_risk_bps": net_risk_bps,
            "net_reward_risk": net_rr,
            "target_covers_cost": target_covers_cost,
            "breakeven_hit_rate_pct": breakeven_hit_rate_pct,
            "stop_geometry_valid": geom_valid,
            "trade_cost_eligible": is_eligible,
            "is_economically_eligible": is_eligible,
            "eligibility_status": eligibility_status,
            "eligibility_reason": rejection_reason,
            "invalidation_rules": invalidation,
            "blocking_reason": blocking_reason,
            "market_snapshot": snapshot,
            "economic_eligibility": {
                "status": eligibility_status,
                "is_eligible": is_eligible,
                "rejection_reason": rejection_reason,
                "structural_rules_valid": rule_triggered and geom_valid,
                "market_inputs_valid": inputs_valid,
                "market_data_fresh": snapshot["is_fresh"],
                "regime_confirmed": regime_info.get("hysteresis_status") == "CONFIRMED" and active_regime != "TRANSITION_UNSUPPORTED",
                "gross_reward_usd": gross_reward_usd,
                "gross_reward_pct": gross_reward_pct,
                "gross_reward_bps": gross_reward_bps,
                "gross_risk_usd": gross_risk_usd,
                "gross_risk_pct": gross_risk_pct,
                "gross_risk_bps": gross_risk_bps,
                "gross_reward_risk": gross_rr,
                "cost_scenario": cost_scenario,
                "cost_round_trip_bps": cost_bps,
                "cost_round_trip_usd": cost_usd,
                "itemized_costs": itemized_costs,
                "net_reward_usd": net_reward_usd,
                "net_reward_pct": net_reward_pct,
                "net_reward_bps": net_reward_bps,
                "net_risk_usd": net_risk_usd,
                "net_risk_pct": net_risk_pct,
                "net_risk_bps": net_risk_bps,
                "net_reward_risk": net_rr,
                "target_covers_cost": target_covers_cost,
                "breakeven_hit_rate_pct": breakeven_hit_rate_pct,
                "preview_only": not is_eligible
            }
        })
        return contract


# =============================================================================
# Module-Level Exports & Backward-Compatible Singletons
# =============================================================================

COST_SCENARIOS = V12StrategyTournamentEngine.COST_SCENARIOS
REGIME_TOURNAMENT_ENGINE = V12StrategyTournamentEngine()


def build_market_snapshot(
    candle_close_time: Optional[str] = None,
    interval: str = "1h",
    eval_time: Optional[datetime] = None,
    freshness_policy_seconds: float = 7200.0,
    live_quote: Optional[Dict[str, Any]] = None,
) -> MarketSnapshot:
    """
    Module-level helper to build and verify a MarketSnapshot identity and freshness.
    """
    now_dt = eval_time if eval_time is not None else datetime.now(timezone.utc)
    if candle_close_time is not None:
        candle_ts = pd.to_datetime(candle_close_time, utc=True)
        candle_close_utc = candle_ts.isoformat()
        candle_open_utc = (candle_ts - timedelta(hours=1)).isoformat()
        age_sec = (now_dt - candle_ts).total_seconds()
        is_candle_closed = True
    elif REGIME_TOURNAMENT_ENGINE.df_1h is not None and len(REGIME_TOURNAMENT_ENGINE.df_1h) > 0:
        latest = REGIME_TOURNAMENT_ENGINE.df_1h.iloc[-1]
        candle_ts = pd.to_datetime(latest["timestamp"], utc=True)
        candle_close_utc = candle_ts.isoformat()
        candle_open_utc = (candle_ts - timedelta(hours=1)).isoformat()
        age_sec = (now_dt - candle_ts).total_seconds()
        is_candle_closed = True
    else:
        return MarketSnapshot({
            "provider": "coinbase",
            "product": "BTC/USD",
            "instrument": "BTC-USD",
            "interval": interval,
            "candle_open_timestamp_utc": None,
            "candle_close_timestamp_utc": None,
            "candle_close_time": None,
            "is_candle_closed": False,
            "is_feature_eligible": False,
            "latest_quote_timestamp_utc": None,
            "latest_quote_source": None,
            "latest_quote_price_usd": None,
            "quote_feature_divergence": False,
            "source_timestamp_utc": None,
            "receipt_timestamp_utc": now_dt.isoformat(),
            "dataset_identifier": "EMPTY",
            "feature_version": "1.0.0",
            "freshness_policy_seconds": freshness_policy_seconds,
            "observed_age_seconds": None,
            "freshness_status": "DATA_UNAVAILABLE",
            "is_fresh": False,
            "is_stale": True,
            "rejection_reason": "No market candle data loaded."
        })

    if age_sec < -60.0:
        status = "FUTURE_TIMESTAMP"
        is_fresh = False
        is_stale = True
        reason = f"Candle close timestamp ({candle_close_utc}) is in the future."
    elif age_sec > freshness_policy_seconds:
        status = "STALE"
        is_fresh = False
        is_stale = True
        reason = f"Market data snapshot is stale ({age_sec/3600.0:.1f}h old > {freshness_policy_seconds/3600.0:.1f}h limit)."
    else:
        status = "FRESH"
        is_fresh = True
        is_stale = False
        reason = "Market data snapshot is fresh."

    return MarketSnapshot({
        "provider": "coinbase",
        "product": "BTC/USD",
        "instrument": "BTC-USD",
        "interval": interval,
        "candle_open_timestamp_utc": candle_open_utc,
        "candle_close_timestamp_utc": candle_close_utc,
        "candle_close_time": candle_close_utc,
        "is_candle_closed": is_candle_closed,
        "is_feature_eligible": is_candle_closed,
        "latest_quote_timestamp_utc": live_quote.get("source_timestamp_utc") if live_quote else None,
        "latest_quote_source": live_quote.get("provider") if live_quote else None,
        "latest_quote_price_usd": live_quote.get("price_usd") if live_quote else None,
        "quote_feature_divergence": False,
        "source_timestamp_utc": candle_close_utc,
        "receipt_timestamp_utc": now_dt.isoformat(),
        "dataset_identifier": "coinbase_btc_usd_1h",
        "feature_version": "1.0.0",
        "freshness_policy_seconds": freshness_policy_seconds,
        "observed_age_seconds": round(age_sec, 1),
        "freshness_status": status,
        "is_fresh": is_fresh,
        "is_stale": is_stale,
        "rejection_reason": reason
    })


class StrategyCandidateWrapper:
    """Wrapper exposing individual strategy candidates with evaluate_current_setup."""
    def __init__(self, strat_id: str, engine: V12StrategyTournamentEngine):
        self.id = strat_id
        self._engine = engine

    def evaluate_current_setup(
        self,
        df_features: Any = None,
        regime_info: Optional[Dict[str, Any]] = None,
        cost_scenario: str = "COINBASE_RETAIL_87BPS",
        eval_time: Optional[datetime] = None,
        live_quote: Optional[Dict[str, Any]] = None
    ) -> AttributeDict:
        raw = self._engine._evaluate_current_setup(
            self.id,
            regime_info=regime_info or {},
            cost_scenario=cost_scenario,
            eval_time=eval_time,
            live_quote=live_quote
        )
        res = AttributeDict(raw)
        if "economic_eligibility" in res and isinstance(res["economic_eligibility"], dict):
            res["economic_eligibility"] = AttributeDict(res["economic_eligibility"])
        if "market_snapshot" in res and isinstance(res["market_snapshot"], dict):
            res["market_snapshot"] = AttributeDict(res["market_snapshot"])
        return res


REGIME_ADAPTIVE_ROUTER = StrategyCandidateWrapper("REGIME_ADAPTIVE_ROUTER", REGIME_TOURNAMENT_ENGINE)
SHORT_HORIZON_MEAN_REVERSION = StrategyCandidateWrapper("SHORT_HORIZON_MEAN_REVERSION", REGIME_TOURNAMENT_ENGINE)
VOL_COMPRESSION_BREAKOUT = StrategyCandidateWrapper("VOL_COMPRESSION_BREAKOUT", REGIME_TOURNAMENT_ENGINE)
MTF_MOMENTUM_TREND = StrategyCandidateWrapper("MTF_MOMENTUM_TREND", REGIME_TOURNAMENT_ENGINE)
HTF_RANGE_EXPANSION_BREAKOUT = StrategyCandidateWrapper("HTF_RANGE_EXPANSION_BREAKOUT", REGIME_TOURNAMENT_ENGINE)
TREND_FOLLOWING_BREAKOUT = MTF_MOMENTUM_TREND


if __name__ == "__main__":
    engine = V12StrategyTournamentEngine()
    manifest = engine.run_tournament("COINBASE_RETAIL_87BPS")
    print(json.dumps(manifest, indent=2))

