"""
data/validate.py — Pure OHLCV integrity validation (no I/O, no side effects).
=============================================================================

Every ingestion path and the feature builder must be able to answer the same
question before writing or consuming market data: *is this candle frame
structurally sound?* This module centralises that answer.

Design contract
---------------
* **Pure:** takes a DataFrame, returns a :class:`ValidationReport`; never
  reads/writes files, never mutates the caller's frame.
* **Dependency-light:** pandas + numpy only.
* **Hard invariants raise, soft anomalies only report.** Hard invariants are
  properties whose violation makes downstream econometrics meaningless (a bar
  with ``high < low`` is not a price; a duplicated timestamp double-counts
  realized variance). Gaps are a *soft* anomaly: they are common in exchange
  history (maintenance windows, outages) and must be reported, not silently
  repaired or fatal.
* **Causal point-in-time only:** this module never sorts/reindexes the frame in
  place, never fills values, and never shifts data. It only inspects.

Hard invariants (any failure -> :class:`DataValidationError`)
-------------------------------------------------------------
1. Required columns present: ``timestamp, open, high, low, close, volume``.
2. Timestamps parseable, non-null, and unique (no duplicate timestamps).
3. Timestamps strictly increasing once sorted.
4. ``high >= low`` and ``high >= max(open, close)`` and
   ``low <= min(open, close)``.
5. ``volume >= 0`` and finite.
6. No NaN in OHLC (and therefore no NaN volume).

Soft checks (reported only, never raise)
----------------------------------------
* Empty frame.
* ``available_time`` column missing or earlier than ``timestamp``
  (a candle cannot be known before it opens).
* Bar spacing: inferred interval, largest gap in bars, number of gaps > 2 bars,
  and count of intervals that are not a whole multiple of the inferred bar size.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

__all__ = [
    "REQUIRED_OHLCV_COLUMNS",
    "DataValidationError",
    "ValidationReport",
    "validate_ohlcv",
    "GAP_ALERT_BARS",
]

#: Columns that must be present in a frame validated as OHLCV.
REQUIRED_OHLCV_COLUMNS: Tuple[str, ...] = (
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
)

#: Gaps strictly larger than this many missing bars are counted/reported.
GAP_ALERT_BARS: int = 2


class DataValidationError(ValueError):
    """Raised when a hard OHLCV invariant fails.

    The full :class:`ValidationReport` is attached as ``.report`` so callers can
    log structured diagnostics (``exc.report.to_dict()``) instead of a string.
    """

    def __init__(self, report: "ValidationReport") -> None:
        self.report = report
        detail = "; ".join(report.errors) if report.errors else "unknown validation failure"
        super().__init__(f"{report.name} failed OHLCV validation: {detail}")


@dataclass
class ValidationReport:
    """Structured outcome of :func:`validate_ohlcv`.

    Attributes
    ----------
    name:
        Logical dataset name used in messages/logs.
    rows:
        Number of rows inspected.
    columns:
        Columns present on the inspected frame.
    errors:
        Hard-invariant violations. Non-empty implies the frame must not be
        written or used for feature construction.
    warnings:
        Soft anomalies (gaps, missing ``available_time``, ...).
    duplicate_timestamps:
        Number of timestamps that appear more than once.
    largest_gap_bars:
        Largest number of *missing* bars between consecutive observations
        (0 when the frame is contiguous or has fewer than 2 rows).
    gaps_over_2_bars:
        Count of consecutive-observation gaps strictly larger than
        :data:`GAP_ALERT_BARS` missing bars.
    largest_gap_start / largest_gap_end:
        ISO-8601 boundaries of the largest gap (``None`` when no gap).
    inferred_interval:
        Inferred bar spacing as a pandas Timedelta (not JSON-serialisable;
        ``to_dict`` renders it as a string).
    """

    name: str
    rows: int
    columns: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duplicate_timestamps: int = 0
    largest_gap_bars: int = 0
    gaps_over_2_bars: int = 0
    largest_gap_start: Optional[str] = None
    largest_gap_end: Optional[str] = None
    inferred_interval: Optional[pd.Timedelta] = None

    @property
    def ok(self) -> bool:
        """True when no hard invariant failed."""
        return not self.errors

    def to_dict(self) -> Dict[str, Any]:
        """JSON-friendly representation suitable for structured logging."""
        return {
            "name": self.name,
            "ok": self.ok,
            "rows": self.rows,
            "columns": list(self.columns),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "duplicate_timestamps": self.duplicate_timestamps,
            "largest_gap_bars": self.largest_gap_bars,
            "gaps_over_2_bars": self.gaps_over_2_bars,
            "largest_gap_start": self.largest_gap_start,
            "largest_gap_end": self.largest_gap_end,
            "inferred_interval": (
                None if self.inferred_interval is None else str(self.inferred_interval)
            ),
        }


def _iso(ts: Any) -> Optional[str]:
    if ts is None or pd.isna(ts):
        return None
    try:
        return pd.Timestamp(ts).isoformat()
    except Exception:
        return str(ts)


def _numeric(series: pd.Series) -> Tuple[pd.Series, int]:
    """Return (float series, count of originally non-null non-numeric entries)."""
    converted = pd.to_numeric(series, errors="coerce")
    coerced = converted.isna() & series.notna()
    return converted.astype(float), int(coerced.sum())


def _check_gaps(
    timestamps: pd.Series, report: ValidationReport
) -> None:
    """Populate gap statistics on ``report``. Never raises."""
    if len(timestamps) < 2:
        return
    ts = pd.to_datetime(pd.Series(timestamps).reset_index(drop=True), utc=True)
    if ts.isna().any():
        return
    deltas = ts.diff().iloc[1:]
    if deltas.empty:
        return
    positive = deltas[deltas > pd.Timedelta(0)]
    if positive.empty:
        return
    interval = positive.min()
    if interval <= pd.Timedelta(0):
        return
    report.inferred_interval = interval

    ratio = deltas / interval
    # Bars missing between consecutive observations (0 for a contiguous step).
    missing = np.rint(ratio.to_numpy(dtype=float)).astype(np.int64) - 1
    missing = np.clip(missing, 0, None)

    irregular = int(
        np.sum(np.abs(ratio.to_numpy(dtype=float) - np.rint(ratio.to_numpy(dtype=float))) > 1e-6)
    )
    if irregular:
        report.warnings.append(
            f"{irregular} bar spacing(s) are not whole multiples of the inferred "
            f"interval {interval}; exchange outages or partial candles suspected"
        )

    largest = int(missing.max()) if missing.size else 0
    report.largest_gap_bars = largest
    report.gaps_over_2_bars = int(np.sum(missing > GAP_ALERT_BARS))

    if largest > 0:
        idx = int(np.argmax(missing)) + 1  # position in `ts` of the gap's right edge
        report.largest_gap_start = _iso(ts.iloc[idx - 1])
        report.largest_gap_end = _iso(ts.iloc[idx])
        report.warnings.append(
            f"largest gap is {largest} missing bar(s) "
            f"({report.largest_gap_start} -> {report.largest_gap_end})"
        )
    if report.gaps_over_2_bars:
        report.warnings.append(
            f"{report.gaps_over_2_bars} gap(s) exceed {GAP_ALERT_BARS} missing bars"
        )


def validate_ohlcv(df: pd.DataFrame, name: str = "ohlcv") -> ValidationReport:
    """Validate an OHLCV candle frame against hard and soft invariants.

    Parameters
    ----------
    df:
        Candle frame. Must contain :data:`REQUIRED_OHLCV_COLUMNS`. Extra columns
        (``available_time``, funding, ...) are allowed and ignored except for
        the soft ``available_time`` check.
    name:
        Label used in error messages and reports.

    Returns
    -------
    ValidationReport
        Always returned when every hard invariant holds; contains soft warnings
        and gap statistics.

    Raises
    ------
    DataValidationError
        Subclass of :class:`ValueError` carrying the report, when any hard
        invariant fails. All detected violations are aggregated into one
        report so callers see the complete picture in a single run.
    """
    report = ValidationReport(name=name, rows=0)
    if not isinstance(df, pd.DataFrame):
        report.errors.append(f"expected a pandas DataFrame, got {type(df).__name__}")
        raise DataValidationError(report)

    report.rows = int(len(df))
    report.columns = [str(c) for c in df.columns]

    missing_cols = [c for c in REQUIRED_OHLCV_COLUMNS if c not in df.columns]
    if missing_cols:
        report.errors.append(f"missing required columns: {missing_cols}")
        raise DataValidationError(report)

    if df.empty:
        report.warnings.append("frame is empty; nothing to validate beyond the schema")
        return report

    # ---------------------------------------------------------------- timestamps
    raw_ts = df["timestamp"]
    ts = pd.to_datetime(raw_ts, utc=True, errors="coerce")
    nat_count = int(ts.isna().sum())
    if nat_count:
        report.errors.append(f"{nat_count} timestamp(s) are null or unparseable")

    valid_ts = ts.dropna()
    dup_mask = valid_ts.duplicated(keep=False)
    report.duplicate_timestamps = int(valid_ts.duplicated(keep="first").sum())
    if report.duplicate_timestamps:
        examples = valid_ts[dup_mask].drop_duplicates().head(3).tolist()
        report.errors.append(
            f"{report.duplicate_timestamps} duplicate timestamp(s), e.g. {examples}"
        )

    if not valid_ts.empty:
        # Strictly increasing *after* sorting. When duplicates exist the
        # duplicate error above already covers the non-strict step, so avoid a
        # redundant second message.
        sorted_ts = valid_ts.sort_values()
        diffs = sorted_ts.diff().iloc[1:]
        non_positive = int((diffs <= pd.Timedelta(0)).sum())
        if non_positive and not report.duplicate_timestamps:
            report.errors.append(
                f"timestamps are not strictly increasing after sorting "
                f"({non_positive} non-positive step(s))"
            )

    # -------------------------------------------------------------------- prices
    ohlc = {}
    for col in ("open", "high", "low", "close", "volume"):
        ohlc[col], non_numeric = _numeric(df[col])
        if non_numeric:
            report.errors.append(f"{non_numeric} non-numeric value(s) in column '{col}'")

    for col in ("open", "high", "low", "close"):
        non_finite = int((~np.isfinite(ohlc[col].to_numpy(dtype=float))).sum())
        if non_finite:
            report.errors.append(f"{non_finite} NaN/inf value(s) in column '{col}'")

    high, low = ohlc["high"], ohlc["low"]
    open_, close = ohlc["open"], ohlc["close"]
    volume = ohlc["volume"]

    # Compare only rows where every operand is present, so a NaN row is
    # reported once (above) instead of also producing phantom ordering errors.
    complete = (
        np.isfinite(high.to_numpy(dtype=float))
        & np.isfinite(low.to_numpy(dtype=float))
        & np.isfinite(open_.to_numpy(dtype=float))
        & np.isfinite(close.to_numpy(dtype=float))
    )
    complete = pd.Series(complete, index=high.index)

    high_lt_low = int((complete & (high < low)).sum())
    if high_lt_low:
        report.errors.append(f"{high_lt_low} bar(s) with high < low")

    high_lt_body = int((complete & (high < np.maximum(open_, close))).sum())
    if high_lt_body:
        report.errors.append(
            f"{high_lt_body} bar(s) with high < max(open, close)"
        )

    low_gt_body = int((complete & (low > np.minimum(open_, close))).sum())
    if low_gt_body:
        report.errors.append(
            f"{low_gt_body} bar(s) with low > min(open, close)"
        )

    # -------------------------------------------------------------------- volume
    vol_non_finite = int((~np.isfinite(volume.to_numpy(dtype=float))).sum())
    if vol_non_finite:
        report.errors.append(f"{vol_non_finite} NaN/inf value(s) in column 'volume'")
    negative_vol = int((volume < 0).sum())
    if negative_vol:
        report.errors.append(f"{negative_vol} bar(s) with negative volume")

    # ------------------------------------------------------ soft availability check
    if "available_time" not in df.columns:
        report.warnings.append(
            "no 'available_time' column; point-in-time availability cannot be asserted"
        )
    else:
        avail = pd.to_datetime(df["available_time"], utc=True, errors="coerce")
        known = avail.notna() & ts.notna()
        early = int((known & (avail < ts)).sum())
        if early:
            report.warnings.append(
                f"{early} row(s) have available_time < timestamp (candle known before it opened)"
            )
        if int(avail.isna().sum()):
            report.warnings.append(
                f"{int(avail.isna().sum())} row(s) have null/unparseable available_time"
            )

    # ---------------------------------------------------------------------- gaps
    _check_gaps(valid_ts.sort_values(), report)

    if report.errors:
        raise DataValidationError(report)
    return report
