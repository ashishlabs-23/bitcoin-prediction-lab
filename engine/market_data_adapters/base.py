"""
engine/market_data_adapters/base.py — Normalized Market Data Adapter Contract
=============================================================================
Defines the canonical normalized schema, validation invariants, and abstract
interface for all BTCognitive market data providers.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
import math
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field, field_validator


class FeedFreshnessStatus(str, Enum):
    FRESH = "FRESH"
    DELAYED = "DELAYED"
    STALE = "STALE"
    INCOMPLETE = "INCOMPLETE"
    UNAVAILABLE = "UNAVAILABLE"
    DISCONNECTED = "DISCONNECTED"


class VenueType(str, Enum):
    VENUE_SPECIFIC = "VENUE_SPECIFIC"
    CROSS_VENUE_AGGREGATE = "CROSS_VENUE_AGGREGATE"


class NormalizedCandle(BaseModel):
    """
    Canonical, normalized representation of a single OHLCV candlestick bar.
    Enforces strict mathematical extrema and non-negativity invariants.
    """
    provider_id: str = Field(..., description="Unique provider ID (e.g. 'bitstamp', 'coingecko')")
    venue_or_aggregate: VenueType = Field(..., description="Venue specificity classification")
    symbol: str = Field(..., description="Normalized pair symbol (e.g. 'BTC/USD')")
    base_currency: str = Field(..., description="Base currency code (e.g. 'BTC')")
    quote_currency: str = Field(..., description="Quote currency code (e.g. 'USD')")
    interval: str = Field(..., description="Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')")
    open_time_utc: str = Field(..., description="ISO 8601 UTC timestamp of candle open boundary")
    close_time_utc: str = Field(..., description="ISO 8601 UTC timestamp of candle close boundary")
    source_timestamp_utc: str = Field(..., description="Timestamp reported by provider")
    fetched_at_utc: str = Field(..., description="Local system retrieval timestamp in UTC")
    timestamp_epoch: int = Field(..., description="Unix timestamp in seconds for candle open")
    open: float = Field(..., gt=0.0, description="Open price in quote currency")
    high: float = Field(..., gt=0.0, description="High price in quote currency")
    low: float = Field(..., gt=0.0, description="Low price in quote currency")
    close: float = Field(..., gt=0.0, description="Close price in quote currency")
    volume: float = Field(..., ge=0.0, description="Volume in base currency")
    candle_complete: bool = Field(..., description="True if bar is closed; False if active/forming")
    license_reference: str = Field(..., description="Mandatory attribution notice")

    @field_validator("open", "high", "low", "close", "volume")
    @classmethod
    def validate_finite_numbers(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError(f"Candle metric must be finite, received: {v}")
        return v

    @field_validator("high")
    @classmethod
    def validate_high_extremum(cls, v: float, info) -> float:
        data = info.data
        if "open" in data and v < data["open"]:
            raise ValueError(f"High ({v}) cannot be less than Open ({data['open']})")
        if "close" in data and v < data["close"]:
            raise ValueError(f"High ({v}) cannot be less than Close ({data['close']})")
        return v

    @field_validator("low")
    @classmethod
    def validate_low_extremum(cls, v: float, info) -> float:
        data = info.data
        if "open" in data and v > data["open"]:
            raise ValueError(f"Low ({v}) cannot be greater than Open ({data['open']})")
        if "close" in data and v > data["close"]:
            raise ValueError(f"Low ({v}) cannot be greater than Close ({data['close']})")
        if "high" in data and v > data["high"]:
            raise ValueError(f"Low ({v}) cannot be greater than High ({data['high']})")
        return v


class FeedDiagnostics(BaseModel):
    """Metadata regarding request round-trip latency, HTTP status, and provenance."""
    latency_ms: float = Field(..., description="Request latency in milliseconds")
    http_status: int = Field(..., description="HTTP status code from upstream provider")
    raw_payload_sha256: str = Field(..., description="SHA-256 hash of raw provider response")
    error_code: Optional[str] = Field(None, description="Standardized error code if failed")
    error_message: Optional[str] = Field(None, description="Error message description if failed")
    upstream_disclaimer: str = Field(..., description="Mandatory legal attribution notice")
    gap_count: int = Field(0, description="Count of detected missing candle intervals")
    is_fallback: bool = Field(False, description="Strictly False: multi-exchange fallback chains prohibited")


class NormalizedCandleResponse(BaseModel):
    """Canonical API and engine response wrapper for candlestick feeds."""
    provider_id: str = Field(...)
    venue: str = Field(...)
    venue_type: VenueType = Field(...)
    symbol: str = Field(...)
    interval: str = Field(...)
    retrieval_timestamp_utc: str = Field(...)
    freshness_status: FeedFreshnessStatus = Field(...)
    candles: List[NormalizedCandle] = Field(default_factory=list)
    diagnostics: FeedDiagnostics = Field(...)


class IMarketDataProviderAdapter(ABC):
    """
    Abstract interface defining the contract for all market data provider adapters.
    """

    @abstractmethod
    def get_provider_id(self) -> str:
        """Returns unique provider identifier (e.g., 'bitstamp', 'coingecko')."""
        pass

    @abstractmethod
    def get_venue_type(self) -> VenueType:
        """Returns VENUE_SPECIFIC or CROSS_VENUE_AGGREGATE."""
        pass

    @abstractmethod
    def get_attribution_disclaimer(self) -> str:
        """Returns mandatory legal attribution notice."""
        pass

    @abstractmethod
    def get_supported_intervals(self) -> List[str]:
        """Returns list of supported timeframes (e.g. ['1m', '5m', '15m', '1h', '1d'])."""
        pass

    @abstractmethod
    async def fetch_candles(
        self,
        symbol: str,
        interval: str,
        limit: int = 150,
        mock_raw_response: Optional[Dict[str, Any]] = None
    ) -> NormalizedCandleResponse:
        """
        Fetches and validates candles. If mock_raw_response is provided,
        parses the mock payload deterministically without external network calls.
        """
        pass

    @staticmethod
    def validate_series_invariants(candles: List[NormalizedCandle], expected_interval_sec: int) -> Tuple[bool, List[str]]:
        """
        Validates series-level invariants:
        1. Strictly monotonic in time: T_{i} > T_{i-1}
        2. No duplicate timestamps
        3. Gap detection (T_{i} - T_{i-1} > expected_interval_sec)
        4. Zero synthetic candle fabrication
        """
        errors = []
        if not candles:
            return True, errors

        seen_timestamps = set()
        for i, c in enumerate(candles):
            if c.timestamp_epoch in seen_timestamps:
                errors.append(f"DUPLICATE_TIMESTAMP: Bar {i} timestamp {c.timestamp_epoch} is duplicate")
            seen_timestamps.add(c.timestamp_epoch)

            if i > 0:
                prev = candles[i - 1]
                delta = c.timestamp_epoch - prev.timestamp_epoch
                if delta <= 0:
                    errors.append(
                        f"NON_MONOTONIC_TIMESTAMPS: Bar {i} ({c.timestamp_epoch}) <= Bar {i-1} ({prev.timestamp_epoch})"
                    )
                elif delta > int(expected_interval_sec * 1.1):
                    # Flag explicit gap without synthesizing bars
                    errors.append(
                        f"INTERVAL_GAP_DETECTED: Gap of {delta}s between {prev.timestamp_epoch} and {c.timestamp_epoch} (expected {expected_interval_sec}s)"
                    )

        return len(errors) == 0, errors

