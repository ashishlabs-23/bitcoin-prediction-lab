"""
research/entry_tp_sl/pit_features.py
====================================
Point-in-Time (PIT) feature extraction engine.
Guarantees:
- Strict causality: available_timestamp <= decision_timestamp.
- Causal rolling calculations with no forward lookahead.
- Rejection of future data.

Status: FROZEN PIT FEATURE STORE (Phase 6E)
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd


FEATURE_NAMES = [
    "vol_atr14_pct",
    "vol_realized_24h",
    "vol_parkinson_24h",
    "mom_roc_4",
    "mom_roc_16",
    "mom_rsi_14",
    "vol_volume_ratio_20",
    "trend_sma50_diff",
    "setup_sweep_mag",
    "setup_range_width",
    "setup_bars_since",
    "time_hour_sin",
    "time_hour_cos"
]


class PITTimingProvenanceError(ValueError):
    """Raised when source timestamp and point-in-time availability evidence is absent or invalid."""


@dataclass(frozen=True)
class PITTimingContract:
    source_id: str
    timestamp_column: str
    timestamp_role: str
    timestamp_unit: str
    timezone: str
    availability_column: str
    availability_rule: str
    verified: bool


def validate_pit_timing_contract(
    timing_contract: Optional[PITTimingContract],
) -> PITTimingContract:
    """Require explicit, verified close-time and availability semantics before research processing."""
    if timing_contract is None:
        raise PITTimingProvenanceError(
            "PIT timing provenance is unresolved; supply a verified source/timestamp contract "
            "before reading market data or generating outcomes."
        )
    required = {
        "source_id": timing_contract.source_id,
        "timestamp_column": timing_contract.timestamp_column,
        "availability_column": timing_contract.availability_column,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise PITTimingProvenanceError(
            "PIT timing contract is missing required identity fields: " + ", ".join(missing)
        )
    if timing_contract.verified is not True:
        raise PITTimingProvenanceError("PIT timing contract is not verified.")
    if timing_contract.timestamp_role != "bar_close":
        raise PITTimingProvenanceError(
            "PIT processing requires an explicitly verified bar_close timestamp role."
        )
    if timing_contract.timestamp_unit != "unix_seconds" or timing_contract.timezone != "UTC":
        raise PITTimingProvenanceError(
            "PIT processing requires explicitly verified Unix-second UTC timestamps."
        )
    expected_rule = (
        f"{timing_contract.availability_column} <= {timing_contract.timestamp_column}"
    )
    if timing_contract.availability_rule != expected_rule:
        raise PITTimingProvenanceError(
            f"PIT availability rule must be explicitly declared as {expected_rule!r}."
        )
    return timing_contract


def validate_pit_timing_data(
    df: pd.DataFrame,
    timing_contract: Optional[PITTimingContract],
) -> None:
    """Verify declared timing columns and row-wise availability before features or outcomes."""
    contract = validate_pit_timing_contract(timing_contract)
    missing = [
        column
        for column in (contract.timestamp_column, contract.availability_column)
        if column not in df.columns
    ]
    if missing:
        raise PITTimingProvenanceError(
            "PIT timing columns are absent from the source: " + ", ".join(missing)
        )
    timestamps = pd.to_numeric(df[contract.timestamp_column], errors="coerce")
    available = pd.to_numeric(df[contract.availability_column], errors="coerce")
    if timestamps.isna().any() or available.isna().any():
        raise PITTimingProvenanceError("PIT timestamps must be finite numeric Unix seconds.")
    if not np.isfinite(timestamps.to_numpy(dtype=float)).all() or not np.isfinite(
        available.to_numpy(dtype=float)
    ).all():
        raise PITTimingProvenanceError("PIT timestamps must be finite numeric Unix seconds.")
    if (timestamps % 1 != 0).any() or (available % 1 != 0).any():
        raise PITTimingProvenanceError("PIT timestamps must be integer Unix seconds.")
    if not timestamps.is_monotonic_increasing or timestamps.duplicated().any():
        raise PITTimingProvenanceError(
            "PIT source timestamps must be strictly increasing and unique."
        )
    if (available > timestamps).any():
        raise PITTimingProvenanceError(
            "PIT availability violation: a row is not available by its declared decision time."
        )


def compute_pit_features_table(
    df_15m: pd.DataFrame,
    timing_contract: Optional[PITTimingContract] = None,
) -> pd.DataFrame:
    """
    Computes causal PIT features on 15-minute aggregated decision bars.
    Returns a dataframe indexed by Timestamp with causal feature columns.
    """
    contract = validate_pit_timing_contract(timing_contract)
    validate_pit_timing_data(df_15m, contract)
    if contract.timestamp_column != "Timestamp":
        raise PITTimingProvenanceError(
            "The setup and feature pipeline requires the verified decision-time column 'Timestamp'."
        )
    df = df_15m.copy().sort_values(contract.timestamp_column).reset_index(drop=True)
    closes = df['Close']
    highs = df['High']
    lows = df['Low']
    volumes = df['Volume']
    timestamps = df[contract.timestamp_column]

    # 1. Volatility features
    prev_close = closes.shift(1)
    tr = pd.concat([
        highs - lows,
        (highs - prev_close).abs(),
        (lows - prev_close).abs()
    ], axis=1).max(axis=1)
    atr14 = tr.rolling(window=14).mean()
    df['vol_atr14_pct'] = atr14 / closes

    log_rets = np.log(closes / prev_close)
    df['vol_realized_24h'] = log_rets.rolling(window=96).std() * np.sqrt(96)

    # Parkinson volatility (high-low estimator over 96 bars)
    hl_log_sq = (np.log(highs / lows) ** 2) / (4.0 * np.log(2.0))
    df['vol_parkinson_24h'] = np.sqrt(hl_log_sq.rolling(window=96).mean() * 96)

    # 2. Momentum features
    df['mom_roc_4'] = (closes - closes.shift(4)) / closes.shift(4)
    df['mom_roc_16'] = (closes - closes.shift(16)) / closes.shift(16)

    # Causal RSI 14
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['mom_rsi_14'] = 100.0 - (100.0 / (1.0 + rs))

    # 3. Volume and trend features
    vol_sma20 = volumes.rolling(window=20).mean()
    df['vol_volume_ratio_20'] = volumes / (vol_sma20 + 1e-9)

    sma50 = closes.rolling(window=50).mean()
    df['trend_sma50_diff'] = (closes - sma50) / sma50

    # 4. Time features (UTC)
    dt_series = pd.to_datetime(timestamps, unit='s', utc=True)
    hours = dt_series.dt.hour + dt_series.dt.minute / 60.0
    df['time_hour_sin'] = np.sin(2.0 * np.pi * hours / 24.0)
    df['time_hour_cos'] = np.cos(2.0 * np.pi * hours / 24.0)

    return df
