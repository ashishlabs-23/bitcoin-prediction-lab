"""
engine/market_data_adapters/coingecko.py — CoinGecko Commercial Market Data Adapter
===================================================================================
Concrete implementation of IMarketDataProviderAdapter for CoinGecko aggregated market data.
Enforces CoinGecko attribution, display-only scope, and strict AI/ML model-training prohibition.
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import httpx

from engine.market_data_adapters.base import (
    IMarketDataProviderAdapter,
    NormalizedCandle,
    NormalizedCandleResponse,
    FeedDiagnostics,
    FeedFreshnessStatus,
    VenueType,
)

logger = logging.getLogger("btcognitive.adapter.coingecko")

COINGECKO_INTERVAL_MAP = {
    "1h": 3600,
    "1d": 86400,
}


class CoinGeckoAdapter(IMarketDataProviderAdapter):
    """
    Adapter for CoinGecko Aggregated BTC Market Data.
    Strictly restricted to visual chart display. AI/ML model training is banned by terms.
    """

    def __init__(self, api_base_url: str = "https://api.coingecko.com/api/v3"):
        self.api_base_url = api_base_url
        self.provider_id = "coingecko"
        self.venue = "COINGECKO_AGGREGATE"
        self.venue_type = VenueType.CROSS_VENUE_AGGREGATE
        self.disclaimer = (
            "Data provided by CoinGecko. Customer-facing display permitted under paid commercial plan with attribution. "
            "AI/ML model training and public dataset creation strictly prohibited under CoinGecko API terms."
        )

    def get_provider_id(self) -> str:
        return self.provider_id

    def get_venue_type(self) -> VenueType:
        return self.venue_type

    def get_attribution_disclaimer(self) -> str:
        return self.disclaimer

    def get_supported_intervals(self) -> List[str]:
        return list(COINGECKO_INTERVAL_MAP.keys())

    def assert_ai_training_permitted(self):
        """
        Governance safeguard: Enforces CoinGecko API terms prohibiting AI/ML model training.
        """
        raise PermissionError(
            "GOVERNANCE VIOLATION: CoinGecko API Terms of Service strictly prohibit "
            "AI/ML model training, evaluation, validation, and public dataset creation on its data."
        )

    def _format_iso(self, epoch_sec: int) -> str:
        return datetime.fromtimestamp(epoch_sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    async def fetch_candles(
        self,
        symbol: str = "BTC/USD",
        interval: str = "1h",
        limit: int = 150,
        mock_raw_response: Optional[List[List[float]]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> NormalizedCandleResponse:
        """
        Fetches and validates CoinGecko OHLC candles.
        If mock_raw_response is provided, operates deterministically in offline QA mode.
        """
        retrieval_epoch = int(time.time())
        retrieval_iso = self._format_iso(retrieval_epoch)

        norm_symbol = symbol.replace("-", "/").upper()
        if norm_symbol != "BTC/USD":
            return NormalizedCandleResponse(
                provider_id=self.provider_id,
                venue=self.venue,
                venue_type=self.venue_type,
                symbol=symbol,
                interval=interval,
                retrieval_timestamp_utc=retrieval_iso,
                freshness_status=FeedFreshnessStatus.UNAVAILABLE,
                candles=[],
                diagnostics=FeedDiagnostics(
                    latency_ms=0.0,
                    http_status=422,
                    raw_payload_sha256="",
                    error_code="UNSUPPORTED_SYMBOL",
                    error_message=f"CoinGecko adapter configured for BTC/USD; received {symbol}",
                    upstream_disclaimer=self.disclaimer,
                    gap_count=0,
                    is_fallback=False,
                ),
            )

        if interval not in COINGECKO_INTERVAL_MAP:
            return NormalizedCandleResponse(
                provider_id=self.provider_id,
                venue=self.venue,
                venue_type=self.venue_type,
                symbol=symbol,
                interval=interval,
                retrieval_timestamp_utc=retrieval_iso,
                freshness_status=FeedFreshnessStatus.UNAVAILABLE,
                candles=[],
                diagnostics=FeedDiagnostics(
                    latency_ms=0.0,
                    http_status=422,
                    raw_payload_sha256="",
                    error_code="UNSUPPORTED_INTERVAL",
                    error_message=f"Interval '{interval}' is unsupported on CoinGecko self-serve. Supported: {list(COINGECKO_INTERVAL_MAP.keys())}",
                    upstream_disclaimer=self.disclaimer,
                    gap_count=0,
                    is_fallback=False,
                ),
            )

        step_seconds = COINGECKO_INTERVAL_MAP[interval]
        start_time = time.perf_counter()

        http_status = 200
        raw_data = None
        error_code = None
        error_message = None

        if mock_raw_response is not None:
            raw_data = mock_raw_response
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        else:
            adapter_enabled = os.environ.get("BTC_ENABLE_PROVIDER_ADAPTER", "false").lower() == "true"
            if not adapter_enabled:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return NormalizedCandleResponse(
                    provider_id=self.provider_id,
                    venue=self.venue,
                    venue_type=self.venue_type,
                    symbol=norm_symbol,
                    interval=interval,
                    retrieval_timestamp_utc=retrieval_iso,
                    freshness_status=FeedFreshnessStatus.UNAVAILABLE,
                    candles=[],
                    diagnostics=FeedDiagnostics(
                        latency_ms=latency_ms,
                        http_status=403,
                        raw_payload_sha256="",
                        error_code="PROVIDER_ADAPTER_DISABLED",
                        error_message="Live provider adapter is disabled by feature flag (BTC_ENABLE_PROVIDER_ADAPTER=false).",
                        upstream_disclaimer=self.disclaimer,
                        gap_count=0,
                        is_fallback=False,
                    ),
                )

            # Live API call
            days = 1 if interval == "1h" else 30
            url = f"{self.api_base_url}/coins/bitcoin/ohlc?vs_currency=usd&days={days}"
            try:
                local_client = client or httpx.AsyncClient(timeout=4.0)
                async with local_client as http:
                    res = await http.get(url)
                    http_status = res.status_code
                    if res.status_code == 200:
                        raw_data = res.json()
                    elif res.status_code == 429:
                        error_code = "RATE_LIMIT_EXCEEDED"
                        error_message = "CoinGecko API rate limit exceeded."
                    else:
                        error_code = "UPSTREAM_HTTP_ERROR"
                        error_message = f"CoinGecko returned HTTP {res.status_code}"
            except httpx.TimeoutException:
                http_status = 504
                error_code = "UPSTREAM_TIMEOUT"
                error_message = "Connection to CoinGecko timed out after 4.0s."
            except Exception as ex:
                http_status = 502
                error_code = "UPSTREAM_DISCONNECTED"
                error_message = str(ex)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if raw_data is None:
            return NormalizedCandleResponse(
                provider_id=self.provider_id,
                venue=self.venue,
                venue_type=self.venue_type,
                symbol=norm_symbol,
                interval=interval,
                retrieval_timestamp_utc=retrieval_iso,
                freshness_status=FeedFreshnessStatus.UNAVAILABLE,
                candles=[],
                diagnostics=FeedDiagnostics(
                    latency_ms=latency_ms,
                    http_status=http_status,
                    raw_payload_sha256="",
                    error_code=error_code or "DATA_UNAVAILABLE",
                    error_message=error_message or "Failed acquiring data from CoinGecko feed.",
                    upstream_disclaimer=self.disclaimer,
                    gap_count=0,
                    is_fallback=False,
                ),
            )

        payload_bytes = json.dumps(raw_data, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        # Parse CoinGecko format: [[time_ms, open, high, low, close], ...]
        normalized_candles: List[NormalizedCandle] = []
        parse_errors = []

        for idx, bar in enumerate(raw_data):
            try:
                t_sec = int(bar[0] // 1000)
                o = float(bar[1])
                h = float(bar[2])
                l = float(bar[3])
                c = float(bar[4])
                v = 0.0  # CoinGecko /ohlc endpoint does not bundle per-candle volume

                is_closed = (t_sec + step_seconds) <= retrieval_epoch

                nc = NormalizedCandle(
                    provider_id=self.provider_id,
                    venue_or_aggregate=self.venue_type,
                    symbol=norm_symbol,
                    base_currency="BTC",
                    quote_currency="USD",
                    interval=interval,
                    open_time_utc=self._format_iso(t_sec),
                    close_time_utc=self._format_iso(t_sec + step_seconds),
                    source_timestamp_utc=self._format_iso(t_sec),
                    fetched_at_utc=retrieval_iso,
                    timestamp_epoch=t_sec,
                    open=o,
                    high=h,
                    low=l,
                    close=c,
                    volume=v,
                    candle_complete=is_closed,
                    license_reference=self.disclaimer,
                )
                normalized_candles.append(nc)
            except Exception as e:
                parse_errors.append(f"Row {idx} invalid: {e}")

        if parse_errors:
            return NormalizedCandleResponse(
                provider_id=self.provider_id,
                venue=self.venue,
                venue_type=self.venue_type,
                symbol=norm_symbol,
                interval=interval,
                retrieval_timestamp_utc=retrieval_iso,
                freshness_status=FeedFreshnessStatus.INCOMPLETE,
                candles=[],
                diagnostics=FeedDiagnostics(
                    latency_ms=latency_ms,
                    http_status=422,
                    raw_payload_sha256=payload_hash,
                    error_code="MALFORMED_OHLCV_FIELDS",
                    error_message=f"Failed parsing CoinGecko candle fields: {parse_errors[:3]}",
                    upstream_disclaimer=self.disclaimer,
                    gap_count=0,
                    is_fallback=False,
                ),
            )

        is_valid_series, series_errors = self.validate_series_invariants(normalized_candles, step_seconds)
        gap_count = sum(1 for err in series_errors if "INTERVAL_GAP_DETECTED" in err)

        if any("NON_MONOTONIC" in err or "DUPLICATE" in err for err in series_errors):
            return NormalizedCandleResponse(
                provider_id=self.provider_id,
                venue=self.venue,
                venue_type=self.venue_type,
                symbol=norm_symbol,
                interval=interval,
                retrieval_timestamp_utc=retrieval_iso,
                freshness_status=FeedFreshnessStatus.INCOMPLETE,
                candles=[],
                diagnostics=FeedDiagnostics(
                    latency_ms=latency_ms,
                    http_status=422,
                    raw_payload_sha256=payload_hash,
                    error_code="ORDERING_OR_DUPLICATE_ERROR",
                    error_message=f"Series integrity check failed: {series_errors}",
                    upstream_disclaimer=self.disclaimer,
                    gap_count=gap_count,
                    is_fallback=False,
                ),
            )

        latest_bar = normalized_candles[-1]
        age_sec = retrieval_epoch - (latest_bar.timestamp_epoch + step_seconds)
        if age_sec > (2 * step_seconds):
            freshness = FeedFreshnessStatus.STALE
        elif age_sec > step_seconds:
            freshness = FeedFreshnessStatus.DELAYED
        else:
            freshness = FeedFreshnessStatus.FRESH

        return NormalizedCandleResponse(
            provider_id=self.provider_id,
            venue=self.venue,
            venue_type=self.venue_type,
            symbol=norm_symbol,
            interval=interval,
            retrieval_timestamp_utc=retrieval_iso,
            freshness_status=freshness,
            candles=normalized_candles,
            diagnostics=FeedDiagnostics(
                latency_ms=latency_ms,
                http_status=http_status,
                raw_payload_sha256=payload_hash,
                error_code=None,
                error_message=None,
                upstream_disclaimer=self.disclaimer,
                gap_count=gap_count,
                is_fallback=False,
            ),
        )

