"""
engine/market_data_adapters/bitstamp.py — Bitstamp Commercial Market Data Adapter
================================================================================
Concrete implementation of IMarketDataProviderAdapter for Bitstamp exchange data.
Enforces Bitstamp DLA compliance, step interval validation, and zero synthetic fabrication.
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

logger = logging.getLogger("btcognitive.adapter.bitstamp")

# Supported step intervals in seconds according to Bitstamp OHLC documentation
BITSTAMP_INTERVAL_MAP = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "12h": 43200,
    "1d": 86400,
}


class BitstampAdapter(IMarketDataProviderAdapter):
    """
    Adapter for Bitstamp BTC/USD Spot Candles under commercial Data License Agreement.
    """

    def __init__(self, api_base_url: str = "https://www.bitstamp.net/api/v2"):
        self.api_base_url = api_base_url
        self.provider_id = "bitstamp"
        self.venue = "BITSTAMP"
        self.venue_type = VenueType.VENUE_SPECIFIC
        self.disclaimer = "Market Data provided by Bitstamp under commercial Data License Agreement."

    def get_provider_id(self) -> str:
        return self.provider_id

    def get_venue_type(self) -> VenueType:
        return self.venue_type

    def get_attribution_disclaimer(self) -> str:
        return self.disclaimer

    def get_supported_intervals(self) -> List[str]:
        return list(BITSTAMP_INTERVAL_MAP.keys())

    def _format_iso(self, epoch_sec: int) -> str:
        return datetime.fromtimestamp(epoch_sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    async def fetch_candles(
        self,
        symbol: str = "BTC/USD",
        interval: str = "1h",
        limit: int = 150,
        mock_raw_response: Optional[Dict[str, Any]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> NormalizedCandleResponse:
        """
        Fetches and validates Bitstamp OHLC candles.
        If mock_raw_response is provided, operates deterministically in offline QA mode.
        """
        retrieval_epoch = int(time.time())
        retrieval_iso = self._format_iso(retrieval_epoch)

        # 1. Validate Symbol & Interval Support
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
                    error_message=f"Bitstamp adapter supports only BTC/USD; received {symbol}",
                    upstream_disclaimer=self.disclaimer,
                    gap_count=0,
                    is_fallback=False,
                ),
            )

        if interval not in BITSTAMP_INTERVAL_MAP:
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
                    error_message=f"Interval '{interval}' is unsupported by Bitstamp. Supported: {list(BITSTAMP_INTERVAL_MAP.keys())}",
                    upstream_disclaimer=self.disclaimer,
                    gap_count=0,
                    is_fallback=False,
                ),
            )

        step_seconds = BITSTAMP_INTERVAL_MAP[interval]
        start_time = time.perf_counter()

        # 2. Acquire Raw Data (Mock or Live if enabled)
        http_status = 200
        raw_data = None
        error_code = None
        error_message = None

        if mock_raw_response is not None:
            raw_data = mock_raw_response
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        else:
            # Check feature flag before making live network call
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
            pair_slug = "btcusd"
            url = f"{self.api_base_url}/ohlc/{pair_slug}/?step={step_seconds}&limit={min(limit, 1000)}&exclude_current_candle=true"
            try:
                local_client = client or httpx.AsyncClient(timeout=4.0)
                async with local_client as http:
                    res = await http.get(url)
                    http_status = res.status_code
                    if res.status_code == 200:
                        raw_data = res.json()
                    elif res.status_code == 429:
                        error_code = "RATE_LIMIT_EXCEEDED"
                        error_message = "Bitstamp API rate limit exceeded."
                    else:
                        error_code = "UPSTREAM_HTTP_ERROR"
                        error_message = f"Bitstamp returned HTTP {res.status_code}"
            except Exception as ex:
                # If Windows OpenSSL handshake resets (Imperva WAF), delegate to PowerShell SChannel fetcher
                if sys.platform == "win32":
                    try:
                        from engine.bitstamp_market_data_service import get_bitstamp_service
                        ps_success, ps_data, ps_err, ps_lat, _ = get_bitstamp_service().fetch_raw_bitstamp_ohlcv(limit=limit)
                        if ps_success and ps_data:
                            raw_data = ps_data
                            http_status = 200
                        else:
                            http_status = 502
                            error_code = "UPSTREAM_DISCONNECTED"
                            error_message = ps_err or str(ex)
                    except Exception as sub_ex:
                        http_status = 502
                        error_code = "UPSTREAM_DISCONNECTED"
                        error_message = f"{ex} -> {sub_ex}"
                else:
                    http_status = 504 if isinstance(ex, httpx.TimeoutException) else 502
                    error_code = "UPSTREAM_TIMEOUT" if isinstance(ex, httpx.TimeoutException) else "UPSTREAM_DISCONNECTED"
                    error_message = str(ex)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 3. Handle Ingestion Failures
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
                    error_message=error_message or "Failed acquiring data from Bitstamp feed.",
                    upstream_disclaimer=self.disclaimer,
                    gap_count=0,
                    is_fallback=False,
                ),
            )

        payload_bytes = json.dumps(raw_data, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        # 4. Parse & Transform Raw Bitstamp OHLC
        ohlc_list = raw_data.get("data", {}).get("ohlc", [])
        if not ohlc_list and isinstance(raw_data.get("ohlc"), list):
            ohlc_list = raw_data["ohlc"]

        if not ohlc_list:
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
                    raw_payload_sha256=payload_hash,
                    error_code="EMPTY_SERIES",
                    error_message="Bitstamp returned zero candle bars.",
                    upstream_disclaimer=self.disclaimer,
                    gap_count=0,
                    is_fallback=False,
                ),
            )

        normalized_candles: List[NormalizedCandle] = []
        parse_errors = []

        for idx, bar in enumerate(ohlc_list):
            try:
                t_sec = int(bar.get("timestamp") or 0)
                o = float(bar.get("open") or 0.0)
                h = float(bar.get("high") or 0.0)
                l = float(bar.get("low") or 0.0)
                c = float(bar.get("close") or 0.0)
                v = float(bar.get("volume") or 0.0)

                # Determine if candle is closed
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
                    error_message=f"Failed parsing Bitstamp candle fields: {parse_errors[:3]}",
                    upstream_disclaimer=self.disclaimer,
                    gap_count=0,
                    is_fallback=False,
                ),
            )

        # 5. Invariant Validation (Monotonicity & Gaps)
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

        # 6. Evaluate Freshness
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

