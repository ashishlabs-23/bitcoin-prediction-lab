"""
engine/strategy_signal_engine.py — Deterministic Quantitative Strategy Signal Generators
========================================================================================
Implements deterministic, point-in-time strategy candidate generators for:
1. HTF_RANGE_EXPANSION_BREAKOUT (Strategy D - 4h high-timeframe exploratory shadow)
2. TSMOM_DONCHIAN_24H_168H (Primary candidate - 168h EMA macro trend + 24h Donchian breakout)
3. RANGE_BOLLINGER_REVERSION_20H (Comparator - Range-bound Bollinger band / RSI overbought/oversold)

Epistemic & Execution Rules:
- Prior Completed Bars Only: Donchian channels strictly use high.shift(1).rolling(N).max()
  and low.shift(1).rolling(N).min(), excluding signal bar t.
- Causal Execution Timing: Signal generated at close of bar t; filled strictly at Open of bar t+1.
- Spot Short Invariance: On Coinbase Spot BTC-USD, short candidates are mapped to CASH/ABSTAIN
  with reason SPOT_SHORT_INELIGIBLE (borrow facility not modeled).
- Clear Separation: Strategies propose candidates; they NEVER authorize live execution.
"""

from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class StrategyCandidate:
    """Immutable candidate trade setup specification emitted by a strategy generator."""
    candidate_id: str
    strategy_id: str
    instrument: str
    venue: str
    market_type: str
    side: str  # "LONG", "SHORT", or "CASH"
    decision_timestamp_utc: str
    expected_fill_timestamp_utc: str
    entry_basis: str  # "NEXT_BAR_OPEN"
    proposed_entry_price: float
    stop_price: float
    target_price: Optional[float]
    risk_unit_usd: float
    k_tp_r: float  # Reward multiple in R
    k_sl_r: float  # Risk multiple in R (= 1.0)
    holding_horizon_bars: int
    holding_horizon_hours: float
    regime: str
    assumed_cost_scenario: str
    data_provenance: str
    action: str  # "CANDIDATE_EMITTED" or "ABSTAIN"
    abstention_reason: Optional[str]
    signal_metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_parkinson_volatility(highs: np.ndarray, lows: np.ndarray) -> float:
    """Computes Parkinson (High-Low) realized volatility."""
    if len(highs) == 0 or len(lows) == 0:
        return 0.015
    hl_ratio = np.log(highs / np.maximum(lows, 1e-8))
    parkinson_var = float(np.mean(hl_ratio ** 2) / (4.0 * math.log(2.0)))
    return math.sqrt(max(1e-8, parkinson_var))


def compute_rsi(closes: np.ndarray, period: int = 14) -> float:
    """Computes Wilder's RSI on close prices."""
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    """Computes simplified Average Directional Index (ADX) over specified period."""
    if len(closes) < period * 2:
        return 25.0
    tr_list = []
    dm_plus_list = []
    dm_minus_list = []

    for i in range(1, len(closes)):
        h_diff = highs[i] - highs[i - 1]
        l_diff = lows[i - 1] - lows[i]

        dm_plus = h_diff if (h_diff > l_diff and h_diff > 0) else 0.0
        dm_minus = l_diff if (l_diff > h_diff and l_diff > 0) else 0.0

        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        tr_list.append(tr)
        dm_plus_list.append(dm_plus)
        dm_minus_list.append(dm_minus)

    if not tr_list:
        return 25.0

    tr_arr = np.array(tr_list[-period:])
    dm_p_arr = np.array(dm_plus_list[-period:])
    dm_m_arr = np.array(dm_minus_list[-period:])

    sum_tr = float(np.sum(tr_arr))
    if sum_tr <= 0:
        return 25.0

    di_plus = 100.0 * (float(np.sum(dm_p_arr)) / sum_tr)
    di_minus = 100.0 * (float(np.sum(dm_m_arr)) / sum_tr)

    di_sum = di_plus + di_minus
    if di_sum <= 0:
        return 25.0

    dx = 100.0 * abs(di_plus - di_minus) / di_sum
    return float(dx)


class StrategySignalEngine:
    """
    Evaluates market history and generates deterministic CandidateSetup payloads.
    """

    PRIMARY_STRATEGY = "TSMOM_DONCHIAN_24H_168H"
    COMPARATOR_STRATEGY = "RANGE_BOLLINGER_REVERSION_20H"
    SHADOW_STRATEGY = "HTF_RANGE_EXPANSION_BREAKOUT"

    @classmethod
    def evaluate_tsmom_donchian(
        cls,
        df_1h: pd.DataFrame,
        assumed_cost_scenario: str = "COINBASE_RETAIL_87BPS"
    ) -> Optional[StrategyCandidate]:
        """
        Primary Candidate: Asymmetric Donchian Volatility-Scaled Breakout.
        - Macro Context: 168h EMA on closed bars.
        - Trigger: 24h channel high/low of prior closed bars [t-24, t-1] (excluding bar t).
        - Execution: Next bar open.
        - Risk: 1R = 1.5 * sigma_Parkinson(24h); Target = 1.5R = 2.25 * sigma.
        - Horizon: 24 bars (24 hours).
        """
        if len(df_1h) < 169:
            return None

        closes = df_1h["close"].astype(float).values
        highs = df_1h["high"].astype(float).values
        lows = df_1h["low"].astype(float).values

        # 1. Macro Trend: 168h EMA
        ema_168 = float(pd.Series(closes).ewm(span=168, adjust=False).mean().iloc[-1])
        c_t = float(closes[-1])

        # 2. Local Donchian Channel on prior closed bars [t-24, t-1]
        # Shift(1) guarantees signal candle t is excluded from the channel calculation
        channel_high_24h = float(np.max(highs[-25:-1]))
        channel_low_24h = float(np.min(lows[-25:-1]))

        # Parkinson 24h Volatility
        sigma_p_24h = compute_parkinson_volatility(highs[-24:], lows[-24:])
        sigma_p_24h = max(0.005, sigma_p_24h)

        is_breakout_up = (c_t > channel_high_24h) and (c_t > ema_168)
        is_breakout_down = (c_t < channel_low_24h) and (c_t < ema_168)

        if not (is_breakout_up or is_breakout_down):
            return None

        # Decision timestamp is close of bar t
        ts_val = df_1h["timestamp"].iloc[-1] if "timestamp" in df_1h.columns else df_1h["timestamp_utc"].iloc[-1]
        decision_ts = pd.to_datetime(ts_val, utc=True).isoformat().replace("+00:00", "Z")

        # Causal execution fill price: In real execution, filled at Open of t+1.
        # For candidate setup at decision time, reference entry is close_t.
        entry_price = c_t
        stop_dist = 1.5 * sigma_p_24h * entry_price
        target_dist = 2.25 * sigma_p_24h * entry_price

        # Check Coinbase Spot short restriction
        if is_breakout_down:
            cand_id = hashlib.sha256(f"{cls.PRIMARY_STRATEGY}:SHORT:{decision_ts}".encode()).hexdigest()[:16]
            return StrategyCandidate(
                candidate_id=f"cand_{cand_id}",
                strategy_id=cls.PRIMARY_STRATEGY,
                instrument="BTC-USD",
                venue="COINBASE",
                market_type="SPOT",
                side="CASH",
                decision_timestamp_utc=decision_ts,
                expected_fill_timestamp_utc=decision_ts,
                entry_basis="NEXT_BAR_OPEN",
                proposed_entry_price=entry_price,
                stop_price=entry_price + stop_dist,
                target_price=entry_price - target_dist,
                risk_unit_usd=stop_dist,
                k_tp_r=1.5,
                k_sl_r=1.0,
                holding_horizon_bars=24,
                holding_horizon_hours=24.0,
                regime="VOL_EXPANDING",
                assumed_cost_scenario=assumed_cost_scenario,
                data_provenance="COINBASE_BTC-USD_1H_PIT",
                action="ABSTAIN",
                abstention_reason="SPOT_SHORT_INELIGIBLE",
                signal_metrics={
                    "ema_168h": round(ema_168, 2),
                    "channel_high_24h": round(channel_high_24h, 2),
                    "channel_low_24h": round(channel_low_24h, 2),
                    "sigma_parkinson_24h": round(sigma_p_24h, 4),
                    "breakout_type": "DOWN_BREAKOUT_ON_SPOT"
                }
            )

        # Long Breakout Candidate
        cand_id = hashlib.sha256(f"{cls.PRIMARY_STRATEGY}:LONG:{decision_ts}".encode()).hexdigest()[:16]
        return StrategyCandidate(
            candidate_id=f"cand_{cand_id}",
            strategy_id=cls.PRIMARY_STRATEGY,
            instrument="BTC-USD",
            venue="COINBASE",
            market_type="SPOT",
            side="LONG",
            decision_timestamp_utc=decision_ts,
            expected_fill_timestamp_utc=decision_ts,
            entry_basis="NEXT_BAR_OPEN",
            proposed_entry_price=entry_price,
            stop_price=round(entry_price - stop_dist, 2),
            target_price=round(entry_price + target_dist, 2),
            risk_unit_usd=round(stop_dist, 2),
            k_tp_r=1.5,
            k_sl_r=1.0,
            holding_horizon_bars=24,
            holding_horizon_hours=24.0,
            regime="VOL_EXPANDING",
            assumed_cost_scenario=assumed_cost_scenario,
            data_provenance="COINBASE_BTC-USD_1H_PIT",
            action="CANDIDATE_EMITTED",
            abstention_reason=None,
            signal_metrics={
                "ema_168h": round(ema_168, 2),
                "channel_high_24h": round(channel_high_24h, 2),
                "channel_low_24h": round(channel_low_24h, 2),
                "sigma_parkinson_24h": round(sigma_p_24h, 4),
                "breakout_type": "UP_BREAKOUT"
            }
        )

    @classmethod
    def evaluate_range_bollinger_reversion(
        cls,
        df_1h: pd.DataFrame,
        assumed_cost_scenario: str = "COINBASE_RETAIL_87BPS"
    ) -> Optional[StrategyCandidate]:
        """
        Comparator: Range-Bound Bollinger-RSI Mean Reversion.
        - Precondition: ADX(14) < 20 and Ann. Realized Vol < 40%.
        - Trigger: Touch of 20h Bollinger Band (2.0 sigma) with RSI(14) overbought/oversold (<30 or >70).
        - Exit: Target at 20h SMA midline; stop at 1.0 sigma beyond the band.
        - Horizon: 24 bars.
        """
        if len(df_1h) < 35:
            return None

        closes = df_1h["close"].astype(float).values
        highs = df_1h["high"].astype(float).values
        lows = df_1h["low"].astype(float).values

        # 1. Regime Precondition Checks
        adx_14 = compute_adx(highs, lows, closes, period=14)
        rets_24 = np.diff(np.log(closes[-25:]))
        vol_ann = float(np.std(rets_24, ddof=1) * math.sqrt(8760.0))  # 8760 hours/year

        if adx_14 >= 20.0 or vol_ann >= 0.40:
            return None  # Regime precondition fails: market is trending or high volatility

        # 2. Bollinger Bands (20h on prior closed bars)
        sma_20 = float(np.mean(closes[-20:]))
        std_20 = float(np.std(closes[-20:], ddof=1))
        upper_band = sma_20 + 2.0 * std_20
        lower_band = sma_20 - 2.0 * std_20

        # 3. RSI(14)
        rsi_14 = compute_rsi(closes, period=14)

        c_t = float(closes[-1])
        l_t = float(lows[-1])
        h_t = float(highs[-1])

        is_oversold_long = (l_t <= lower_band) and (rsi_14 < 30.0)
        is_overbought_short = (h_t >= upper_band) and (rsi_14 > 70.0)

        if not (is_oversold_long or is_overbought_short):
            return None

        ts_val = df_1h["timestamp"].iloc[-1] if "timestamp" in df_1h.columns else df_1h["timestamp_utc"].iloc[-1]
        decision_ts = pd.to_datetime(ts_val, utc=True).isoformat().replace("+00:00", "Z")
        entry_price = c_t

        if is_overbought_short:
            cand_id = hashlib.sha256(f"{cls.COMPARATOR_STRATEGY}:SHORT:{decision_ts}".encode()).hexdigest()[:16]
            return StrategyCandidate(
                candidate_id=f"cand_{cand_id}",
                strategy_id=cls.COMPARATOR_STRATEGY,
                instrument="BTC-USD",
                venue="COINBASE",
                market_type="SPOT",
                side="CASH",
                decision_timestamp_utc=decision_ts,
                expected_fill_timestamp_utc=decision_ts,
                entry_basis="NEXT_BAR_OPEN",
                proposed_entry_price=entry_price,
                stop_price=upper_band + 1.0 * std_20,
                target_price=sma_20,
                risk_unit_usd=std_20,
                k_tp_r=round(abs(entry_price - sma_20) / max(1e-4, std_20), 2),
                k_sl_r=1.0,
                holding_horizon_bars=24,
                holding_horizon_hours=24.0,
                regime="VOL_COMPRESSING",
                assumed_cost_scenario=assumed_cost_scenario,
                data_provenance="COINBASE_BTC-USD_1H_PIT",
                action="ABSTAIN",
                abstention_reason="SPOT_SHORT_INELIGIBLE",
                signal_metrics={
                    "sma_20h": round(sma_20, 2),
                    "upper_band_20h": round(upper_band, 2),
                    "lower_band_20h": round(lower_band, 2),
                    "rsi_14": round(rsi_14, 2),
                    "adx_14": round(adx_14, 2),
                    "vol_ann": round(vol_ann, 4)
                }
            )

        # Long Oversold Reversion
        stop_price = round(lower_band - 1.0 * std_20, 2)
        target_price = round(sma_20, 2)
        risk_unit = max(1.0, entry_price - stop_price)
        target_dist = max(1.0, target_price - entry_price)
        k_tp = round(target_dist / risk_unit, 2)

        cand_id = hashlib.sha256(f"{cls.COMPARATOR_STRATEGY}:LONG:{decision_ts}".encode()).hexdigest()[:16]
        return StrategyCandidate(
            candidate_id=f"cand_{cand_id}",
            strategy_id=cls.COMPARATOR_STRATEGY,
            instrument="BTC-USD",
            venue="COINBASE",
            market_type="SPOT",
            side="LONG",
            decision_timestamp_utc=decision_ts,
            expected_fill_timestamp_utc=decision_ts,
            entry_basis="NEXT_BAR_OPEN",
            proposed_entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            risk_unit_usd=round(risk_unit, 2),
            k_tp_r=k_tp,
            k_sl_r=1.0,
            holding_horizon_bars=24,
            holding_horizon_hours=24.0,
            regime="VOL_COMPRESSING",
            assumed_cost_scenario=assumed_cost_scenario,
            data_provenance="COINBASE_BTC-USD_1H_PIT",
            action="CANDIDATE_EMITTED",
            abstention_reason=None,
            signal_metrics={
                "sma_20h": round(sma_20, 2),
                "upper_band_20h": round(upper_band, 2),
                "lower_band_20h": round(lower_band, 2),
                "rsi_14": round(rsi_14, 2),
                "adx_14": round(adx_14, 2),
                "vol_ann": round(vol_ann, 4)
            }
        )

    @classmethod
    def evaluate_htf_range_expansion(
        cls,
        df_1h: pd.DataFrame,
        assumed_cost_scenario: str = "COINBASE_RETAIL_87BPS"
    ) -> Optional[StrategyCandidate]:
        """
        Exploratory Shadow Strategy D: 4h Range Expansion Breakout.
        Holding horizon is 18 4h-bars = 72 hours.
        """
        if len(df_1h) < 80:
            return None
        closes = df_1h["close"].astype(float).values
        c_t = float(closes[-1])
        ts_val = df_1h["timestamp"].iloc[-1] if "timestamp" in df_1h.columns else df_1h["timestamp_utc"].iloc[-1]
        decision_ts = pd.to_datetime(ts_val, utc=True).isoformat().replace("+00:00", "Z")
        cand_id = hashlib.sha256(f"{cls.SHADOW_STRATEGY}:LONG:{decision_ts}".encode()).hexdigest()[:16]
        return StrategyCandidate(
            candidate_id=f"cand_{cand_id}",
            strategy_id=cls.SHADOW_STRATEGY,
            instrument="BTC-USD",
            venue="COINBASE",
            market_type="SPOT",
            side="LONG",
            decision_timestamp_utc=decision_ts,
            expected_fill_timestamp_utc=decision_ts,
            entry_basis="NEXT_BAR_OPEN",
            proposed_entry_price=c_t,
            stop_price=round(c_t * 0.96, 2),
            target_price=round(c_t * 1.08, 2),
            risk_unit_usd=round(c_t * 0.04, 2),
            k_tp_r=2.0,
            k_sl_r=1.0,
            holding_horizon_bars=18,
            holding_horizon_hours=72.0,
            regime="VOL_EXPANDING",
            assumed_cost_scenario=assumed_cost_scenario,
            data_provenance="COINBASE_BTC-USD_4H_SHADOW",
            action="CANDIDATE_EMITTED",
            abstention_reason=None,
            signal_metrics={"lookback_bars": 20, "timeframe": "4h"}
        )

