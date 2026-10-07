"""
research/entry_tp_sl/detector_spec.py
=====================================
Formal specifications and configuration parameters for structural setup detectors:
- A1: Liquidity Sweep / Reclaim
- A2: Range Reclaim

Status: FROZEN DETECTOR SPECIFICATION (Phase 6C)
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class SweepReclaimConfig:
    """Configuration for A1: Liquidity Sweep / Reclaim setup."""
    setup_name: str = "A1_SWEEP_RECLAIM"
    swing_lookback_bars: int = 24  # 24 * 15m = 6 hours swing high/low
    sweep_min_pct: float = 0.0005  # At least 5 bps penetration beyond swing level
    sweep_max_pct: float = 0.0200  # Max 200 bps penetration (avoid runaway breakouts)
    reclaim_confirmation_window: int = 2  # Must reclaim within 2 bars (30m)
    cooldown_bars: int = 4  # 1 hour cooldown between identical setup signals


@dataclass(frozen=True)
class RangeReclaimConfig:
    """Configuration for A2: Range Reclaim setup."""
    setup_name: str = "A2_RANGE_RECLAIM"
    range_lookback_bars: int = 48  # 48 * 15m = 12 hours range definition
    range_quantile_low: float = 0.15  # Lower range boundary
    range_quantile_high: float = 0.85  # Upper range boundary
    reclaim_buffer_pct: float = 0.0010  # 10 bps penetration inside range for confirmation
    cooldown_bars: int = 4  # 1 hour cooldown
