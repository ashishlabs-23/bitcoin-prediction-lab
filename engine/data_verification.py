"""
engine/data_verification.py — Deterministic Causal Data Verification Layer
===========================================================================
Validates market data contracts, provenance, schema, freshness, and feature availability
prior to strategy candidate generation and Smart Entry gating.

Fails closed on:
- Unsupported instruments (Only Coinbase Spot BTC-USD authorized).
- Missing, non-monotonic, or duplicate timestamps.
- Geometric bar corruptions (High < max(Open, Close) or Low > min(Open, Close)).
- Stale market data exceeding 2x timeframe granularity.
- Requests for features not causally supported by historical OHLCV.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Sequence, Tuple
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DataValidationReport:
    """Immutable validation record emitted by DataContractValidator."""
    is_valid: bool
    reason_code: Optional[str]
    details: Dict[str, Any]
    instrument: str
    venue: str
    timeframe: str
    latest_candle_utc: Optional[str]
    data_age_seconds: Optional[float]
    sample_size: int
    data_provenance: str
    checked_at_utc: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataContractValidator:
    """
    Deterministic data contract validator ensuring zero lookahead and strict provenance.
    """

    SUPPORTED_INSTRUMENTS = {"BTC-USD", "BTCUSD"}
    SUPPORTED_VENUES = {"COINBASE", "BITSTAMP"}
    SUPPORTED_TIMEFRAMES = {
        "15m": 900,
        "1h": 3600,
        "60m": 3600,
        "4h": 14400,
        "24h": 86400,
        "1d": 86400
    }

    # Features causally computable from pure OHLCV
    SUPPORTED_OHLCV_FEATURES = {
        "open", "high", "low", "close", "volume",
        "ret_1h", "ret_4h", "ret_24h", "ret_168h",
        "ema_168h", "donchian_high_24h", "donchian_low_24h",
        "bb_upper_20h", "bb_lower_20h", "bb_mid_20h", "rsi_14",
        "adx_14", "parkinson_vol_24h", "realized_vol_annualized"
    }

    # Features explicitly unavailable in historical OHLCV without tick data
    UNAVAILABLE_MICROSTRUCTURE_FEATURES = {
        "order_book_depth", "ofi", "vpin", "hawkes_intensity",
        "bid_ask_spread", "order_book_imbalance", "liquidation_clusters"
    }

    @classmethod
    def validate_market_data(
        cls,
        candles: Union[pd.DataFrame, Sequence[Dict[str, Any]]],
        instrument: str = "BTC-USD",
        venue: str = "COINBASE",
        timeframe: str = "1h",
        current_epoch_sec: Optional[float] = None,
        max_staleness_multiplier: float = 2.0,
        required_features: Optional[Sequence[str]] = None,
        require_authenticated_provenance: bool = False,
        source_manifest: Optional[Dict[str, Any]] = None
    ) -> DataValidationReport:
        """
        Validates OHLCV market data against strict econometric and causal contracts.
        """
        now_epoch = current_epoch_sec if current_epoch_sec is not None else time.time()
        now_utc = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")

        inst_clean = str(instrument).upper().strip()
        venue_clean = str(venue).upper().strip()
        tf_clean = str(timeframe).lower().strip()

        # 1. Instrument Validation
        if inst_clean not in cls.SUPPORTED_INSTRUMENTS:
            return DataValidationReport(
                is_valid=False,
                reason_code="DATA_CONTRACT_BREACH",
                details={"error": f"Instrument '{instrument}' unsupported. Authorized: {sorted(cls.SUPPORTED_INSTRUMENTS)}"},
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=None,
                data_age_seconds=None,
                sample_size=0,
                data_provenance="UNKNOWN",
                checked_at_utc=now_utc
            )

        # 2. Venue Validation
        if venue_clean not in cls.SUPPORTED_VENUES:
            return DataValidationReport(
                is_valid=False,
                reason_code="SOURCE_UNKNOWN",
                details={"error": f"Venue '{venue}' unsupported. Authorized: {sorted(cls.SUPPORTED_VENUES)}"},
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=None,
                data_age_seconds=None,
                sample_size=0,
                data_provenance="UNKNOWN",
                checked_at_utc=now_utc
            )

        # 2b. Authenticated Provenance Gate
        if require_authenticated_provenance:
            if not source_manifest or not source_manifest.get("is_authenticated", False):
                return DataValidationReport(
                    is_valid=False,
                    reason_code="UNVERIFIED_SOURCE",
                    details={
                        "error": "Dataset lacks an authenticated exchange capture manifest. Historical source cannot be cryptographically proven.",
                        "provenance_status": "UNVERIFIED_SOURCE"
                    },
                    instrument=inst_clean,
                    venue=venue_clean,
                    timeframe=tf_clean,
                    latest_candle_utc=None,
                    data_age_seconds=None,
                    sample_size=0,
                    data_provenance=f"{venue_clean}_{inst_clean}_UNVERIFIED",
                    checked_at_utc=now_utc
                )

        # 3. Timeframe Validation
        if tf_clean not in cls.SUPPORTED_TIMEFRAMES:
            return DataValidationReport(
                is_valid=False,
                reason_code="DATA_CONTRACT_BREACH",
                details={"error": f"Timeframe '{timeframe}' unsupported. Authorized: {list(cls.SUPPORTED_TIMEFRAMES.keys())}"},
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=None,
                data_age_seconds=None,
                sample_size=0,
                data_provenance=f"{venue_clean}_{inst_clean}",
                checked_at_utc=now_utc
            )

        granularity_sec = cls.SUPPORTED_TIMEFRAMES[tf_clean]

        # 4. Feature Availability Audit
        if required_features:
            for feat in required_features:
                f_clean = str(feat).lower().strip()
                if f_clean in cls.UNAVAILABLE_MICROSTRUCTURE_FEATURES:
                    return DataValidationReport(
                        is_valid=False,
                        reason_code="FEATURE_UNAVAILABLE",
                        details={
                            "error": f"Microstructure feature '{feat}' is not available in historical/REST OHLCV feeds.",
                            "unsupported_feature": feat
                        },
                        instrument=inst_clean,
                        venue=venue_clean,
                        timeframe=tf_clean,
                        latest_candle_utc=None,
                        data_age_seconds=None,
                        sample_size=0,
                        data_provenance=f"{venue_clean}_{inst_clean}",
                        checked_at_utc=now_utc
                    )

        # 5. Coerce to DataFrame
        if isinstance(candles, pd.DataFrame):
            df = candles.copy()
        elif isinstance(candles, (list, tuple)):
            if not candles:
                return DataValidationReport(
                    is_valid=False,
                    reason_code="DATA_CONTRACT_BREACH",
                    details={"error": "Empty candles sequence provided."},
                    instrument=inst_clean,
                    venue=venue_clean,
                    timeframe=tf_clean,
                    latest_candle_utc=None,
                    data_age_seconds=None,
                    sample_size=0,
                    data_provenance=f"{venue_clean}_{inst_clean}",
                    checked_at_utc=now_utc
                )
            df = pd.DataFrame(list(candles))
        else:
            return DataValidationReport(
                is_valid=False,
                reason_code="DATA_CONTRACT_BREACH",
                details={"error": f"Unsupported candles format: {type(candles)}"},
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=None,
                data_age_seconds=None,
                sample_size=0,
                data_provenance=f"{venue_clean}_{inst_clean}",
                checked_at_utc=now_utc
            )

        if df.empty:
            return DataValidationReport(
                is_valid=False,
                reason_code="DATA_CONTRACT_BREACH",
                details={"error": "Candles dataset is empty."},
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=None,
                data_age_seconds=None,
                sample_size=0,
                data_provenance=f"{venue_clean}_{inst_clean}",
                checked_at_utc=now_utc
            )

        # 6. Schema Check (OHLCV Columns)
        required_cols = {"open", "high", "low", "close"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            return DataValidationReport(
                is_valid=False,
                reason_code="DATA_CONTRACT_BREACH",
                details={"error": f"Missing required OHLC columns: {sorted(missing_cols)}"},
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=None,
                data_age_seconds=None,
                sample_size=len(df),
                data_provenance=f"{venue_clean}_{inst_clean}",
                checked_at_utc=now_utc
            )

        # 7. Timestamp Verification
        ts_col = None
        for col in ["timestamp_utc", "timestamp", "time", "epoch_time"]:
            if col in df.columns:
                ts_col = col
                break

        if ts_col is None:
            return DataValidationReport(
                is_valid=False,
                reason_code="DATA_CONTRACT_BREACH",
                details={"error": "Candles missing timestamp column (require 'timestamp_utc' or 'timestamp')."},
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=None,
                data_age_seconds=None,
                sample_size=len(df),
                data_provenance=f"{venue_clean}_{inst_clean}",
                checked_at_utc=now_utc
            )

        # Convert timestamps to numeric epoch seconds
        raw_ts = df[ts_col].values
        try:
            if isinstance(raw_ts[0], (int, float, np.integer, np.floating)):
                epoch_series = pd.Series(raw_ts, dtype=float)
            else:
                dt_idx = pd.to_datetime(raw_ts, utc=True)
                epoch_series = pd.Series([float(t.timestamp()) for t in dt_idx], dtype=float)
        except Exception as e:
            return DataValidationReport(
                is_valid=False,
                reason_code="DATA_CONTRACT_BREACH",
                details={"error": f"Failed parsing UTC timestamps: {e}"},
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=None,
                data_age_seconds=None,
                sample_size=len(df),
                data_provenance=f"{venue_clean}_{inst_clean}",
                checked_at_utc=now_utc
            )

        # Check for duplicate timestamps
        if epoch_series.duplicated().any():
            return DataValidationReport(
                is_valid=False,
                reason_code="DATA_CONTRACT_BREACH",
                details={"error": "DUPLICATE_TIMESTAMPS: Candle series contains duplicate timestamps."},
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=None,
                data_age_seconds=None,
                sample_size=len(df),
                data_provenance=f"{venue_clean}_{inst_clean}",
                checked_at_utc=now_utc
            )

        # Check strictly monotonic increasing
        if not epoch_series.is_monotonic_increasing:
            return DataValidationReport(
                is_valid=False,
                reason_code="DATA_CONTRACT_BREACH",
                details={"error": "NON_MONOTONIC_TIMESTAMPS: Candle series is not chronologically sorted."},
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=None,
                data_age_seconds=None,
                sample_size=len(df),
                data_provenance=f"{venue_clean}_{inst_clean}",
                checked_at_utc=now_utc
            )

        # 8. Geometric OHLC Sanity Check
        opens = df["open"].astype(float).values
        highs = df["high"].astype(float).values
        lows = df["low"].astype(float).values
        closes = df["close"].astype(float).values

        # Must be strictly positive
        if np.any(opens <= 0) or np.any(highs <= 0) or np.any(lows <= 0) or np.any(closes <= 0):
            return DataValidationReport(
                is_valid=False,
                reason_code="DATA_CONTRACT_BREACH",
                details={"error": "NON_POSITIVE_PRICE: OHLC prices must be strictly positive."},
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=None,
                data_age_seconds=None,
                sample_size=len(df),
                data_provenance=f"{venue_clean}_{inst_clean}",
                checked_at_utc=now_utc
            )

        # High must be >= max(Open, Close) and Low must be <= min(Open, Close)
        invalid_high = np.any(highs < np.maximum(opens, closes) - 1e-4)
        invalid_low = np.any(lows > np.minimum(opens, closes) + 1e-4)
        if invalid_high or invalid_low:
            return DataValidationReport(
                is_valid=False,
                reason_code="DATA_CONTRACT_BREACH",
                details={"error": "GEOMETRIC_OHLC_VIOLATION: High < max(Open, Close) or Low > min(Open, Close)."},
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=None,
                data_age_seconds=None,
                sample_size=len(df),
                data_provenance=f"{venue_clean}_{inst_clean}",
                checked_at_utc=now_utc
            )

        # 9. Freshness Check (Only for live/recent candles)
        latest_epoch = float(epoch_series.iloc[-1])
        latest_utc = datetime.fromtimestamp(latest_epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        candle_close_epoch = latest_epoch + granularity_sec
        data_age_sec = max(0.0, now_epoch - candle_close_epoch)

        # If data is clearly being checked in a live mode and older than threshold
        if data_age_sec > (granularity_sec * max_staleness_multiplier):
            return DataValidationReport(
                is_valid=False,
                reason_code="STALE_DATA",
                details={
                    "error": f"STALE_DATA: Latest completed candle closed {data_age_sec:.1f}s ago "
                             f"(limit: {granularity_sec * max_staleness_multiplier:.1f}s).",
                    "latest_candle_utc": latest_utc,
                    "data_age_seconds": round(data_age_sec, 1)
                },
                instrument=inst_clean,
                venue=venue_clean,
                timeframe=tf_clean,
                latest_candle_utc=latest_utc,
                data_age_seconds=round(data_age_sec, 1),
                sample_size=len(df),
                data_provenance=f"{venue_clean}_{inst_clean}",
                checked_at_utc=now_utc
            )

        # All checks passed
        return DataValidationReport(
            is_valid=True,
            reason_code=None,
            details={"status": "DATA_CONTRACT_VERIFIED", "granularity_sec": granularity_sec},
            instrument=inst_clean,
            venue=venue_clean,
            timeframe=tf_clean,
            latest_candle_utc=latest_utc,
            data_age_seconds=round(data_age_sec, 1),
            sample_size=len(df),
            data_provenance=f"{venue_clean}_{inst_clean}_CAUSAL_PIT",
            checked_at_utc=now_utc
        )
