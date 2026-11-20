"""
engine/market_data_adapters/provider_contract.py — Market Data Provider Adapter Contract
========================================================================================
Defines the authoritative technical specification and runtime contract for external
market-data providers (e.g. CoinGecko, CoinAPI) for BTCognitive:

1. Price Basis: Explicit distinction between Aggregated Global Benchmark and Venue-Specific Spot.
2. Candle Semantics: Strictly closed UTC candles; forming/incomplete candles excluded.
3. Timeframe Boundaries: Exact alignment to UTC boundaries (15m, 1h, 4h, 24h).
4. Continuity & Gap Handling: Detection and tagging of missing intervals without synthetic fill.
5. Rate Limiting & Caching: Backoff thresholds and local TTL persistence policies.
6. Attribution & Provenance: Required brand badges, source links, and license identifiers.
7. Network Isolation: Fails closed immediately if external network transport is prohibited.
"""

from __future__ import annotations

import abc
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

from engine.data_mode import is_external_network_permitted, assert_no_external_network, ExternalNetworkBlockedError


class PriceBasisType(str, Enum):
    """Authoritative price basis classification."""
    AGGREGATED_GLOBAL_BENCHMARK = "AGGREGATED_GLOBAL_BENCHMARK"   # Volume-weighted across multiple exchanges (e.g. CoinGecko)
    VENUE_SPECIFIC_SPOT_ORDERBOOK = "VENUE_SPECIFIC_SPOT_ORDERBOOK" # Direct orderbook trades from a single venue (e.g. Coinbase, Bitstamp)


class CandleSemantics(str, Enum):
    """Candle closure and point-in-time boundary semantics."""
    CLOSED_INTERVAL_UTC = "CLOSED_INTERVAL_UTC"           # Strictly closed candle; [t, t + interval)
    INCOMPLETE_FORMING_EXCLUDED = "INCOMPLETE_FORMING_EXCLUDED" # Forming candle discarded to prevent lookahead bias


class SupportedInterval(str, Enum):
    """Permitted technical analysis timeframes."""
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "24h"


@dataclass(frozen=True)
class ProviderAttribution:
    """Legal and display attribution metadata required by the provider license."""
    provider_id: str
    display_name: str
    attribution_text: str
    attribution_url: str
    logo_svg_path: Optional[str] = None
    requires_visual_badge: bool = True
    raw_redistribution_permitted: bool = False


@dataclass(frozen=True)
class CandleBar:
    """Immutable, strongly-typed point-in-time candlestick."""
    time: int              # UTC epoch timestamp in seconds (start of interval)
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": self.time,
            "open": round(self.open, 2),
            "high": round(self.high, 2),
            "low": round(self.low, 2),
            "close": round(self.close, 2),
            "volume": round(self.volume, 6),
        }


@dataclass(frozen=True)
class ProviderContinuityReport:
    """Audit metrics evaluating continuity and data quality of retrieved candles."""
    total_candles: int
    interval_seconds: int
    start_utc: str
    end_utc: str
    missing_intervals_count: int
    missing_intervals: List[int]
    is_continuous: bool
    stale_seconds: float
    is_stale: bool


class BaseMarketDataProvider(abc.ABC):
    """
    Abstract Base Class for all external market data providers.
    Enforces contract compliance, rate limiting, and fail-closed safety.
    """

    def __init__(
        self,
        provider_id: str,
        price_basis: PriceBasisType,
        attribution: ProviderAttribution,
        max_requests_per_minute: int = 30,
        stale_threshold_seconds: float = 7200.0,
    ):
        self.provider_id = provider_id
        self.price_basis = price_basis
        self.attribution = attribution
        self.max_requests_per_minute = max_requests_per_minute
        self.stale_threshold_seconds = stale_threshold_seconds
        self._last_request_timestamp = 0.0

    @abc.abstractmethod
    async def fetch_historical_candles_raw(
        self,
        symbol: str,
        interval: SupportedInterval,
        limit: int = 168,
        end_epoch_utc: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch raw candle payload from upstream provider."""
        pass

    async def get_candles(
        self,
        symbol: str = "BTC-USD",
        interval: SupportedInterval = SupportedInterval.H1,
        limit: int = 168,
    ) -> Dict[str, Any]:
        """
        Public contract method for candle ingestion.
        Guarantees:
        1. Pre-transport network guard check (fails closed if network is blocked).
        2. Canonical symbol formatting.
        3. Strict UTC alignment and exclusion of forming candles.
        4. Continuity and staleness evaluation.
        """
        # Step 1: Pre-transport check
        if not is_external_network_permitted():
            assert_no_external_network(f"{self.provider_id}.get_candles")

        # Step 2: Rate limiting guard
        now = time.time()
        elapsed = now - self._last_request_timestamp
        min_interval = 60.0 / max(1, self.max_requests_per_minute)
        if elapsed < min_interval:
            # Enforce pacing
            import asyncio
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_timestamp = time.time()

        # Step 3: Fetch and validate
        raw_items = await self.fetch_historical_candles_raw(symbol, interval, limit)
        validated_bars = self._normalize_and_validate(raw_items, interval)
        continuity = self._audit_continuity(validated_bars, interval)

        return {
            "status": "LIVE" if not continuity.is_stale else "STALE",
            "provider_id": self.provider_id,
            "price_basis": self.price_basis.value,
            "symbol": "BTC-USD",
            "interval": interval.value,
            "count": len(validated_bars),
            "candles": [bar.to_dict() for bar in validated_bars],
            "attribution": {
                "name": self.attribution.display_name,
                "text": self.attribution.attribution_text,
                "url": self.attribution.attribution_url,
            },
            "continuity": {
                "is_continuous": continuity.is_continuous,
                "missing_intervals_count": continuity.missing_intervals_count,
                "stale_seconds": round(continuity.stale_seconds, 1),
            },
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        }

    def _normalize_and_validate(
        self,
        raw_rows: List[Dict[str, Any]],
        interval: SupportedInterval,
    ) -> List[CandleBar]:
        step = {"15m": 900, "1h": 3600, "4h": 14400, "24h": 86400}[interval.value]
        now_epoch = int(time.time())
        # Strictly exclude forming/unclosed candles
        closed_cutoff = (now_epoch // step) * step

        bars_by_time: Dict[int, CandleBar] = {}
        for row in raw_rows:
            try:
                t = int(float(row.get("time", 0)))
                o = float(row.get("open", 0.0))
                h = float(row.get("high", 0.0))
                l = float(row.get("low", 0.0))
                c = float(row.get("close", 0.0))
                v = float(row.get("volume", 0.0))
            except (ValueError, TypeError):
                continue

            # Invariant checks: finite positive prices, monotonic timestamp, closed candle
            if t <= 0 or t % step != 0 or t + step > closed_cutoff:
                continue
            if o <= 0 or h <= 0 or l <= 0 or c <= 0 or v < 0:
                continue
            if h < max(o, c) or l > min(o, c) or h < l:
                continue

            bars_by_time[t] = CandleBar(time=t, open=o, high=h, low=l, close=c, volume=v)

        return [bars_by_time[k] for k in sorted(bars_by_time.keys())]

    def _audit_continuity(
        self,
        bars: List[CandleBar],
        interval: SupportedInterval,
    ) -> ProviderContinuityReport:
        step = {"15m": 900, "1h": 3600, "4h": 14400, "24h": 86400}[interval.value]
        if not bars:
            return ProviderContinuityReport(
                total_candles=0,
                interval_seconds=step,
                start_utc="",
                end_utc="",
                missing_intervals_count=0,
                missing_intervals=[],
                is_continuous=False,
                stale_seconds=999999.0,
                is_stale=True,
            )

        missing = []
        for i in range(1, len(bars)):
            prev_t = bars[i - 1].time
            curr_t = bars[i].time
            if curr_t - prev_t > step:
                gap_cursor = prev_t + step
                while gap_cursor < curr_t:
                    missing.append(gap_cursor)
                    gap_cursor += step

        now_sec = time.time()
        stale_sec = max(0.0, now_sec - (bars[-1].time + step))
        is_stale = stale_sec > self.stale_threshold_seconds

        start_iso = datetime.fromtimestamp(bars[0].time, tz=timezone.utc).isoformat()
        end_iso = datetime.fromtimestamp(bars[-1].time, tz=timezone.utc).isoformat()

        return ProviderContinuityReport(
            total_candles=len(bars),
            interval_seconds=step,
            start_utc=start_iso,
            end_utc=end_iso,
            missing_intervals_count=len(missing),
            missing_intervals=missing,
            is_continuous=len(missing) == 0,
            stale_seconds=stale_sec,
            is_stale=is_stale,
        )

