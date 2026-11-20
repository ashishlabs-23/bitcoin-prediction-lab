"""
research/entry_intelligence/triple_barrier_labeler.py
======================================================
Triple-Barrier label generation for entry candidates.

Labels each entry with the FIRST barrier touched:
  +1  (TP_FIRST)  : Price reached the upper profit barrier before SL or horizon.
  -1  (SL_FIRST)  : Price reached the lower stop barrier before TP or horizon.
   0  (EXPIRED)   : Neither barrier was touched; position expired at the horizon.
  None (AMBIGUOUS): Data gap or insufficient bars prevented reliable labelling.

RESEARCH BOUNDARY: OFFLINE_RESEARCH_ONLY.
  This module generates research labels for offline model evaluation only.
  It does NOT generate live trading signals or authorize live execution.

Causal integrity rules:
  - Labels are computed from bars AFTER the entry bar.
  - No future price information is used in feature construction.
  - Gap detection prevents false label assignment across discontinuities.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Literal


LABEL_TP_FIRST: int = 1
LABEL_SL_FIRST: int = -1
LABEL_EXPIRED: int = 0
LABEL_AMBIGUOUS: None = None


@dataclass
class TripleBarrierLabel:
    """Immutable triple-barrier outcome label for one entry candidate."""
    entry_idx: int
    entry_timestamp: str
    entry_price: float
    direction: Literal["long", "short"]
    tp_pct: float          # TP barrier distance (%)
    sl_pct: float          # SL barrier distance (%)
    horizon_hours: int

    label: Optional[int]   # +1, -1, 0, or None (ambiguous)
    label_str: str         # Human-readable: TP_FIRST, SL_FIRST, EXPIRED, AMBIGUOUS
    tp_price: float
    sl_price: float
    touch_bar_offset: Optional[int]   # Bar offset when first barrier was touched
    touch_timestamp: Optional[str]    # Timestamp when first barrier was touched
    expiry_return_pct: float          # Return at horizon expiry (direction-adjusted)

    bars_evaluated: int
    hit_dataset_end: bool
    has_gap: bool
    gap_exclusion_reason: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TripleBarrierLabeler:
    """
    Generates triple-barrier outcome labels for entry candidates.

    Args:
        df: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close'].
            Must be sorted ascending by timestamp.
        tp_pct: Take-profit distance from entry price (%).
        sl_pct: Stop-loss distance from entry price (%).
        horizon_hours: Maximum holding period in hours.
        max_gap_seconds: Maximum tolerated gap; entries spanning a gap are labelled AMBIGUOUS.
    """

    REQUIRED_COLUMNS = {"open", "high", "low", "close", "timestamp"}

    def __init__(
        self,
        df: pd.DataFrame,
        tp_pct: float = 1.5,
        sl_pct: float = 0.75,
        horizon_hours: int = 24,
        max_gap_seconds: float = 7200.0,
    ) -> None:
        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"TripleBarrierLabeler: missing columns {missing}")
        if tp_pct <= 0 or sl_pct <= 0:
            raise ValueError("tp_pct and sl_pct must be positive.")
        self._df = df.reset_index(drop=True)
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.horizon_hours = horizon_hours
        self.max_gap_seconds = max_gap_seconds

    def label(
        self,
        entry_idx: int,
        direction: Literal["long", "short"] = "long",
    ) -> TripleBarrierLabel:
        """
        Generate triple-barrier label for one entry candidate.

        Entry is assumed to fill at the OPEN of bar entry_idx + 1.
        """
        df = self._df
        n = len(df)

        entry_bar_idx = entry_idx + 1
        if entry_bar_idx >= n:
            raise IndexError(f"entry_idx {entry_idx} is the last bar; no next bar for entry.")

        entry_price = float(df["open"].iloc[entry_bar_idx])
        entry_ts = str(df["timestamp"].iloc[entry_bar_idx])

        if direction == "long":
            tp_price = entry_price * (1 + self.tp_pct / 100)
            sl_price = entry_price * (1 - self.sl_pct / 100)
        else:  # short
            tp_price = entry_price * (1 - self.tp_pct / 100)
            sl_price = entry_price * (1 + self.sl_pct / 100)

        end_idx = min(entry_bar_idx + self.horizon_hours, n)
        window = df.iloc[entry_bar_idx:end_idx]
        bars_evaluated = len(window)

        # Gap detection
        has_gap = False
        gap_exclusion_reason = None
        if bars_evaluated > 1:
            timestamps = pd.to_datetime(window["timestamp"], utc=True)
            diffs = timestamps.diff().dropna().dt.total_seconds()
            if (diffs > self.max_gap_seconds).any():
                has_gap = True
                gap_exclusion_reason = "DISCONTINUOUS_FORWARD_HORIZON_GAP"

        # Expiry return
        if bars_evaluated > 0:
            final_close = float(window["close"].iloc[-1])
            if direction == "long":
                expiry_return_pct = (final_close - entry_price) / entry_price * 100.0
            else:
                expiry_return_pct = (entry_price - final_close) / entry_price * 100.0
        else:
            expiry_return_pct = 0.0

        # Ambiguous if gap found
        if has_gap:
            return TripleBarrierLabel(
                entry_idx=entry_idx,
                entry_timestamp=entry_ts,
                entry_price=entry_price,
                direction=direction,
                tp_pct=self.tp_pct,
                sl_pct=self.sl_pct,
                horizon_hours=self.horizon_hours,
                label=LABEL_AMBIGUOUS,
                label_str="AMBIGUOUS",
                tp_price=tp_price,
                sl_price=sl_price,
                touch_bar_offset=None,
                touch_timestamp=None,
                expiry_return_pct=round(expiry_return_pct, 6),
                bars_evaluated=bars_evaluated,
                hit_dataset_end=(end_idx >= n),
                has_gap=True,
                gap_exclusion_reason=gap_exclusion_reason,
            )

        # Scan bar-by-bar for first barrier touch
        highs = window["high"].values.astype(float)
        lows = window["low"].values.astype(float)
        ts_list = window["timestamp"].tolist()

        label = LABEL_EXPIRED
        label_str = "EXPIRED"
        touch_bar_offset = None
        touch_timestamp = None

        for bar_i, (h, l) in enumerate(zip(highs, lows)):
            if direction == "long":
                tp_touched = h >= tp_price
                sl_touched = l <= sl_price
            else:
                tp_touched = l <= tp_price
                sl_touched = h >= sl_price

            if tp_touched and sl_touched:
                # Both barriers touched in the same bar; conservative: mark AMBIGUOUS
                label = LABEL_AMBIGUOUS
                label_str = "AMBIGUOUS"
                touch_bar_offset = bar_i
                touch_timestamp = str(ts_list[bar_i])
                break
            elif tp_touched:
                label = LABEL_TP_FIRST
                label_str = "TP_FIRST"
                touch_bar_offset = bar_i
                touch_timestamp = str(ts_list[bar_i])
                break
            elif sl_touched:
                label = LABEL_SL_FIRST
                label_str = "SL_FIRST"
                touch_bar_offset = bar_i
                touch_timestamp = str(ts_list[bar_i])
                break

        return TripleBarrierLabel(
            entry_idx=entry_idx,
            entry_timestamp=entry_ts,
            entry_price=entry_price,
            direction=direction,
            tp_pct=self.tp_pct,
            sl_pct=self.sl_pct,
            horizon_hours=self.horizon_hours,
            label=label,
            label_str=label_str,
            tp_price=round(tp_price, 4),
            sl_price=round(sl_price, 4),
            touch_bar_offset=touch_bar_offset,
            touch_timestamp=touch_timestamp,
            expiry_return_pct=round(expiry_return_pct, 6),
            bars_evaluated=bars_evaluated,
            hit_dataset_end=(end_idx >= n),
            has_gap=False,
            gap_exclusion_reason=None,
        )

    def label_batch(
        self,
        entry_indices: list[int],
        direction: Literal["long", "short"] = "long",
    ) -> pd.DataFrame:
        """Label multiple entries and return as DataFrame."""
        results = []
        for idx in entry_indices:
            try:
                r = self.label(idx, direction)
                results.append(r.to_dict())
            except (IndexError, ValueError) as e:
                results.append({"entry_idx": idx, "error": str(e), "label": None, "label_str": "ERROR"})
        return pd.DataFrame(results)

