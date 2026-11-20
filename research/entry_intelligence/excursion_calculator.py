"""
research/entry_intelligence/excursion_calculator.py
=====================================================
Maximum Favourable Excursion (MFE) and Maximum Adverse Excursion (MAE)
calculator for historical BTCUSD OHLCV candles.

RESEARCH BOUNDARY: OFFLINE_RESEARCH_ONLY.
  No live trading signals. No position management. Read-only.

Usage:
    from research.entry_intelligence.excursion_calculator import ExcursionCalculator
    calc = ExcursionCalculator(df)
    result = calc.compute(entry_idx=1000, direction='long', horizon_hours=24)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Literal


@dataclass
class ExcursionResult:
    """Immutable result for one entry candidate's excursion profile."""
    entry_idx: int
    entry_timestamp: str
    entry_price: float
    direction: Literal["long", "short"]
    horizon_hours: int

    # Raw path excursions (gross, before costs)
    mfe_pct: float          # Maximum Favourable Excursion (%)
    mae_pct: float          # Maximum Adverse Excursion (%)
    final_return_pct: float # Return at horizon expiry (+ = favourable for direction)

    # Temporal characteristics
    mfe_bar_offset: int     # Bar index (from entry) where MFE was reached
    mae_bar_offset: int     # Bar index (from entry) where MAE was reached
    bars_evaluated: int     # Number of bars actually evaluated

    # Data quality flags
    hit_dataset_end: bool   # True if horizon was cut short by end of data
    has_gap: bool           # True if a discontinuity was found in the evaluation window

    @property
    def excursion_quality_ratio(self) -> Optional[float]:
        """EQR = MFE / MAE. Returns None if MAE == 0 (no adverse move)."""
        if self.mae_pct == 0.0:
            return None
        return self.mfe_pct / self.mae_pct

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["excursion_quality_ratio"] = self.excursion_quality_ratio
        return d


class ExcursionCalculator:
    """
    Computes path-dependent MFE and MAE for candidate trade entries.

    Rules (causal / no lookahead):
    - Entry occurs at the OPEN of bar entry_idx + 1
      (i.e. the candle that closes AFTER the signal bar).
    - All evaluation uses High/Low/Close of SUBSEQUENT bars only.
    - Horizon is measured in closed candles after entry bar.
    - If the dataset ends before the horizon completes, hit_dataset_end=True.

    Args:
        df: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close'].
            Must be sorted ascending by timestamp.
    """

    REQUIRED_COLUMNS = {"open", "high", "low", "close", "timestamp"}

    def __init__(self, df: pd.DataFrame) -> None:
        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"ExcursionCalculator: missing columns {missing}")
        self._df = df.reset_index(drop=True)

    def compute(
        self,
        entry_idx: int,
        direction: Literal["long", "short"] = "long",
        horizon_hours: int = 24,
        max_gap_seconds: float = 7200.0,
    ) -> ExcursionResult:
        """
        Compute MFE/MAE excursion for one entry candidate.

        Args:
            entry_idx: Row index of the signal bar (entry fills at OPEN of next bar).
            direction: 'long' (profit from rising prices) or 'short' (falling).
            horizon_hours: Evaluation window in hours after entry.
            max_gap_seconds: Max tolerated gap between candles; flags has_gap=True if exceeded.

        Returns:
            ExcursionResult with complete excursion profile.
        """
        df = self._df
        n = len(df)

        # Entry is at the open of the bar immediately after signal bar
        entry_bar_idx = entry_idx + 1
        if entry_bar_idx >= n:
            raise IndexError(f"entry_idx {entry_idx} is the last bar; no next bar for entry.")

        entry_price = float(df["open"].iloc[entry_bar_idx])
        entry_ts = str(df["timestamp"].iloc[entry_bar_idx])

        # Evaluation window: entry_bar_idx through entry_bar_idx + horizon_hours - 1
        end_idx = min(entry_bar_idx + horizon_hours, n)
        window = df.iloc[entry_bar_idx:end_idx]
        bars_evaluated = len(window)

        # Gap detection
        has_gap = False
        if bars_evaluated > 1:
            timestamps = pd.to_datetime(window["timestamp"], utc=True)
            diffs = timestamps.diff().dropna().dt.total_seconds()
            if (diffs > max_gap_seconds).any():
                has_gap = True

        highs = window["high"].values.astype(float)
        lows = window["low"].values.astype(float)
        closes = window["close"].values.astype(float)

        if direction == "long":
            favourable = (highs - entry_price) / entry_price * 100.0
            adverse = (entry_price - lows) / entry_price * 100.0
            final_return_pct = (closes[-1] - entry_price) / entry_price * 100.0
        else:  # short
            favourable = (entry_price - lows) / entry_price * 100.0
            adverse = (highs - entry_price) / entry_price * 100.0
            final_return_pct = (entry_price - closes[-1]) / entry_price * 100.0

        mfe_pct = float(np.max(favourable))
        mae_pct = float(np.max(adverse))
        mfe_bar_offset = int(np.argmax(favourable))
        mae_bar_offset = int(np.argmax(adverse))

        return ExcursionResult(
            entry_idx=entry_idx,
            entry_timestamp=entry_ts,
            entry_price=entry_price,
            direction=direction,
            horizon_hours=horizon_hours,
            mfe_pct=round(mfe_pct, 6),
            mae_pct=round(mae_pct, 6),
            final_return_pct=round(final_return_pct, 6),
            mfe_bar_offset=mfe_bar_offset,
            mae_bar_offset=mae_bar_offset,
            bars_evaluated=bars_evaluated,
            hit_dataset_end=(end_idx >= n),
            has_gap=has_gap,
        )

    def compute_batch(
        self,
        entry_indices: list[int],
        direction: Literal["long", "short"] = "long",
        horizon_hours: int = 24,
        max_gap_seconds: float = 7200.0,
    ) -> pd.DataFrame:
        """
        Compute MFE/MAE for multiple entry candidates and return as DataFrame.

        Raises ValueError if any entry_idx is invalid; callers should filter first.
        """
        results = []
        for idx in entry_indices:
            try:
                r = self.compute(idx, direction, horizon_hours, max_gap_seconds)
                results.append(r.to_dict())
            except (IndexError, ValueError) as e:
                results.append({
                    "entry_idx": idx, "error": str(e),
                    "mfe_pct": None, "mae_pct": None,
                })
        return pd.DataFrame(results)

