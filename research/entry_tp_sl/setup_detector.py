"""
research/entry_tp_sl/setup_detector.py
======================================
Causal structural setup detector for A1 (Sweep/Reclaim) and A2 (Range Reclaim).
Strictly enforces:
- Detector owns direction (Side.LONG / Side.SHORT / None).
- Pure causal lookback at t0 (no future information).
- Cooldown and duplicate suppression.

Status: FROZEN DETECTOR IMPLEMENTATION (Phase 6C)
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import numpy as np
from research.entry_tp_sl.barrier_contract import Side
from research.entry_tp_sl.detector_spec import SweepReclaimConfig, RangeReclaimConfig


@dataclass(frozen=True)
class SetupEvent:
    setup_id: str
    decision_timestamp: int
    side: Side
    setup_type: str  # "A1_SWEEP_RECLAIM" or "A2_RANGE_RECLAIM"
    reference_price: float
    sweep_magnitude_pct: float
    range_width_pct: float
    bars_since_extreme: int


class StructuralSetupDetector:
    """
    Evaluates 15-minute aggregated decision bars to detect causal structural trade setups.
    """

    def __init__(
        self,
        sweep_cfg: SweepReclaimConfig = SweepReclaimConfig(),
        range_cfg: RangeReclaimConfig = RangeReclaimConfig()
    ):
        self.sweep_cfg = sweep_cfg
        self.range_cfg = range_cfg

    def detect_setups(self, df_15m: pd.DataFrame) -> List[SetupEvent]:
        """
        Scans a 15-minute OHLCV dataframe and returns detected SetupEvents.
        Required columns: ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
        """
        if len(df_15m) < max(self.sweep_cfg.swing_lookback_bars, self.range_cfg.range_lookback_bars) + 5:
            return []

        df = df_15m.copy().reset_index(drop=True)
        highs = df['High'].values
        lows = df['Low'].values
        closes = df['Close'].values
        timestamps = df['Timestamp'].values

        events: List[SetupEvent] = []
        last_event_bar = -999
        last_event_side = None

        swing_lb = self.sweep_cfg.swing_lookback_bars
        range_lb = self.range_cfg.range_lookback_bars

        for i in range(max(swing_lb, range_lb), len(df)):
            t0 = int(timestamps[i])
            curr_high = highs[i]
            curr_low = lows[i]
            curr_close = closes[i]

            # Cooldown check
            if i - last_event_bar < self.sweep_cfg.cooldown_bars:
                continue

            detected_side: Optional[Side] = None
            detected_type: Optional[str] = None
            ref_price: float = curr_close
            sweep_mag: float = 0.0
            range_w: float = 0.0
            bars_since: int = 1

            # ----------------------------------------------------
            # 1. Evaluate A1: Liquidity Sweep / Reclaim
            # ----------------------------------------------------
            prior_highs = highs[i - swing_lb:i]
            prior_lows = lows[i - swing_lb:i]
            swing_high = np.max(prior_highs)
            swing_low = np.min(prior_lows)

            # A1 Bullish Sweep: Low swept below swing_low, but Close reclaimed above swing_low
            if curr_low < swing_low and curr_close > swing_low:
                penetration = (swing_low - curr_low) / swing_low
                if self.sweep_cfg.sweep_min_pct <= penetration <= self.sweep_cfg.sweep_max_pct:
                    detected_side = Side.LONG
                    detected_type = "A1_SWEEP_RECLAIM"
                    ref_price = swing_low
                    sweep_mag = penetration
                    range_w = (swing_high - swing_low) / swing_low
                    bars_since = int(swing_lb - np.argmin(prior_lows))

            # A1 Bearish Sweep: High swept above swing_high, but Close reclaimed below swing_high
            elif curr_high > swing_high and curr_close < swing_high:
                penetration = (curr_high - swing_high) / swing_high
                if self.sweep_cfg.sweep_min_pct <= penetration <= self.sweep_cfg.sweep_max_pct:
                    detected_side = Side.SHORT
                    detected_type = "A1_SWEEP_RECLAIM"
                    ref_price = swing_high
                    sweep_mag = penetration
                    range_w = (swing_high - swing_low) / swing_low
                    bars_since = int(swing_lb - np.argmax(prior_highs))

            # ----------------------------------------------------
            # 2. Evaluate A2: Range Reclaim (if A1 not triggered)
            # ----------------------------------------------------
            if detected_side is None:
                range_window = closes[i - range_lb:i]
                r_low = np.quantile(range_window, self.range_cfg.range_quantile_low)
                r_high = np.quantile(range_window, self.range_cfg.range_quantile_high)

                # Bullish Range Reclaim: dipped below r_low, closed above r_low + buffer
                if curr_low < r_low and curr_close >= r_low * (1.0 + self.range_cfg.reclaim_buffer_pct):
                    detected_side = Side.LONG
                    detected_type = "A2_RANGE_RECLAIM"
                    ref_price = r_low
                    sweep_mag = (r_low - curr_low) / r_low
                    range_w = (r_high - r_low) / r_low
                    bars_since = int(range_lb - np.argmin(lows[i - range_lb:i]))

                # Bearish Range Reclaim: spiked above r_high, closed below r_high - buffer
                elif curr_high > r_high and curr_close <= r_high * (1.0 - self.range_cfg.reclaim_buffer_pct):
                    detected_side = Side.SHORT
                    detected_type = "A2_RANGE_RECLAIM"
                    ref_price = r_high
                    sweep_mag = (curr_high - r_high) / r_high
                    range_w = (r_high - r_low) / r_low
                    bars_since = int(range_lb - np.argmax(highs[i - range_lb:i]))

            # If setup detected, register event
            if detected_side is not None:
                setup_uid = f"SETUP_{detected_type}_{t0}_{detected_side.value}"
                event = SetupEvent(
                    setup_id=setup_uid,
                    decision_timestamp=t0,
                    side=detected_side,
                    setup_type=detected_type,
                    reference_price=float(ref_price),
                    sweep_magnitude_pct=float(sweep_mag),
                    range_width_pct=float(range_w),
                    bars_since_extreme=bars_since
                )
                events.append(event)
                last_event_bar = i
                last_event_side = detected_side

        return events
