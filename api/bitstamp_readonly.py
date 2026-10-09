"""Read-only public Bitstamp BTC/USD one-minute market data.

The API's candle ``timestamp`` is the start of its one-minute interval. This
adapter converts it to the frozen ``INTERVAL_CLOSE`` convention and only
returns bars whose interval has completed.
"""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

import httpx


BITSTAMP_OHLC_URL = "https://www.bitstamp.net/api/v2/ohlc/btcusd/"
REQUEST_TIMEOUT_SECONDS = 5.0
OHLC_STEP_SECONDS = 60
DEFAULT_FRESHNESS_LIMIT_SECONDS = 180
REQUEST_LIMIT = 1000


class ReadStatus(str, Enum):
    """Outcome of a public market-data read."""

    OK = "OK"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    STALE_DATA = "STALE_DATA"
    PROVENANCE_FAILURE = "PROVENANCE_FAILURE"


@dataclass(frozen=True)
class OHLCVBar:
    """Completed BTC/USD candle, timestamped at its interval close in UTC."""

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    source_timestamp: int
    source: str = "bitstamp_public_ohlc"
    venue: str = "BITSTAMP"
    symbol: str = "BTC/USD"
    timestamp_semantics: str = "INTERVAL_CLOSE"


@dataclass(frozen=True)
class BitstampReadResult:
    """Market data plus explicit status and source/freshness provenance."""

    status: ReadStatus
    bars: tuple[OHLCVBar, ...]
    source: str
    venue: str
    symbol: str
    source_timestamp: int | None
    retrieved_at: int
    freshness_limit_seconds: int
    message: str | None = None


class _InvalidPayload(ValueError):
    """Raised when upstream data cannot satisfy the frozen bar contract."""


def _result(
    status: ReadStatus,
    *,
    retrieved_at: int,
    freshness_limit_seconds: int,
    bars: tuple[OHLCVBar, ...] = (),
    message: str | None = None,
) -> BitstampReadResult:
    return BitstampReadResult(
        status=status,
        bars=bars,
        source="bitstamp_public_ohlc",
        venue="BITSTAMP",
        symbol="BTC/USD",
        source_timestamp=bars[-1].source_timestamp if bars else None,
        retrieved_at=retrieved_at,
        freshness_limit_seconds=freshness_limit_seconds,
        message=message,
    )


def _retrieval_epoch(now: datetime | int | float | None) -> int:
    if now is None:
        return int(time.time())
    if isinstance(now, datetime):
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be a timezone-aware datetime")
        return int(now.astimezone(timezone.utc).timestamp())
    if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
        raise ValueError("now must be a finite Unix timestamp or aware datetime")
    return int(now)


def _positive_finite(value: Any, field: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool):
        raise _InvalidPayload(f"{field} must be numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise _InvalidPayload(f"{field} must be numeric") from exc
    if not math.isfinite(parsed) or (parsed < 0 if allow_zero else parsed <= 0):
        raise _InvalidPayload(f"{field} must be finite and {'non-negative' if allow_zero else 'positive'}")
    return parsed


def _source_timestamp(value: Any) -> int:
    if isinstance(value, bool):
        raise _InvalidPayload("candle timestamp must be an integer Unix second")
    if isinstance(value, int):
        timestamp = value
    elif isinstance(value, str) and value.isdecimal():
        timestamp = int(value)
    else:
        raise _InvalidPayload("candle timestamp must be an integer Unix second")
    if timestamp < 0:
        raise _InvalidPayload("candle timestamp cannot be negative")
    return timestamp


def _canonical_pair(value: Any) -> str:
    if not isinstance(value, str):
        raise _InvalidPayload("response pair is missing or invalid")
    return value.strip().upper().replace("/", "").replace("-", "")


def _parse_candles(payload: Any, retrieved_at: int) -> tuple[OHLCVBar, ...]:
    if not isinstance(payload, Mapping):
        raise _InvalidPayload("response must be a JSON object")
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise _InvalidPayload("response data object is missing")
    if _canonical_pair(data.get("pair")) != "BTCUSD":
        raise _InvalidPayload("response pair is not BTC/USD")
    raw_bars = data.get("ohlc")
    if not isinstance(raw_bars, list):
        raise _InvalidPayload("response OHLC collection is missing or invalid")

    bars: list[OHLCVBar] = []
    previous_open: int | None = None
    for item in raw_bars:
        if not isinstance(item, Mapping):
            raise _InvalidPayload("each candle must be a JSON object")
        source_timestamp = _source_timestamp(item.get("timestamp"))
        if source_timestamp % OHLC_STEP_SECONDS != 0:
            raise _InvalidPayload("candle timestamp is not aligned to a one-minute boundary")
        if previous_open is not None and source_timestamp <= previous_open:
            raise _InvalidPayload("candle timestamps must be strictly increasing")
        previous_open = source_timestamp
        if source_timestamp > retrieved_at:
            raise _InvalidPayload("candle timestamp is in the future")

        open_price = _positive_finite(item.get("open"), "open")
        high = _positive_finite(item.get("high"), "high")
        low = _positive_finite(item.get("low"), "low")
        close = _positive_finite(item.get("close"), "close")
        volume = _positive_finite(item.get("volume"), "volume", allow_zero=True)
        if high < max(open_price, close) or low > min(open_price, close) or high < low:
            raise _InvalidPayload("OHLC values are internally inconsistent")

        close_timestamp = source_timestamp + OHLC_STEP_SECONDS
        if close_timestamp <= retrieved_at:
            bars.append(
                OHLCVBar(
                    timestamp=close_timestamp,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                    source_timestamp=source_timestamp,
                )
            )
    return tuple(bars)


async def fetch_bitstamp_btcusd_ohlcv(
    client: httpx.AsyncClient,
    *,
    now: datetime | int | float | None = None,
    freshness_limit_seconds: int = DEFAULT_FRESHNESS_LIMIT_SECONDS,
) -> BitstampReadResult:
    """Read Bitstamp's public BTC/USD one-minute OHLC endpoint.

    The client is deliberately required and is the sole HTTP boundary, so
    callers can supply a controlled transport. No shared client, credentials,
    persistence, or alternate venue is used.
    """

    if (
        isinstance(freshness_limit_seconds, bool)
        or not isinstance(freshness_limit_seconds, int)
        or freshness_limit_seconds <= 0
    ):
        raise ValueError("freshness_limit_seconds must be a positive integer")

    try:
        retrieved_at = _retrieval_epoch(now)
    except ValueError:
        raise

    try:
        response = await client.get(
            BITSTAMP_OHLC_URL,
            params={"step": OHLC_STEP_SECONDS, "limit": REQUEST_LIMIT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
        return _result(
            ReadStatus.DATA_UNAVAILABLE,
            retrieved_at=retrieved_at,
            freshness_limit_seconds=freshness_limit_seconds,
            message=f"Bitstamp request timed out: {type(exc).__name__}",
        )
    except httpx.RequestError as exc:
        return _result(
            ReadStatus.DATA_UNAVAILABLE,
            retrieved_at=retrieved_at,
            freshness_limit_seconds=freshness_limit_seconds,
            message=f"Bitstamp request failed: {type(exc).__name__}",
        )
    retrieved_at = _retrieval_epoch(now) if now is not None else int(time.time())
    if response.status_code != 200:
        return _result(
            ReadStatus.DATA_UNAVAILABLE,
            retrieved_at=retrieved_at,
            freshness_limit_seconds=freshness_limit_seconds,
            message=f"Bitstamp returned HTTP {response.status_code}",
        )

    try:
        bars = _parse_candles(response.json(), retrieved_at)
    except (ValueError, TypeError, OverflowError) as exc:
        return _result(
            ReadStatus.PROVENANCE_FAILURE,
            retrieved_at=retrieved_at,
            freshness_limit_seconds=freshness_limit_seconds,
            message=str(exc),
        )

    if not bars:
        return _result(
            ReadStatus.DATA_UNAVAILABLE,
            retrieved_at=retrieved_at,
            freshness_limit_seconds=freshness_limit_seconds,
            message="No completed Bitstamp candles are available",
        )

    if retrieved_at - bars[-1].timestamp > freshness_limit_seconds:
        return _result(
            ReadStatus.STALE_DATA,
            retrieved_at=retrieved_at,
            freshness_limit_seconds=freshness_limit_seconds,
            bars=bars,
            message="Newest completed Bitstamp candle exceeds the freshness limit",
        )

    return _result(
        ReadStatus.OK,
        retrieved_at=retrieved_at,
        freshness_limit_seconds=freshness_limit_seconds,
        bars=bars,
    )
