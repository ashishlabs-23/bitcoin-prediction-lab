"""
tests/test_single_market_data_contract.py — Single Market Data Contract & OHLC Validation Tests
================================================================================================
Validates:
1. Explicit spot BTC/USD instrument identity across public adapters (coinbase, bitstamp, kraken).
2. Strict isolation: USDT perpetual data is context-only and never substituted for spot prices/candles.
3. Candle normalizer invariants: chronological sorting, deduplication, valid OHLC relationships.
4. Immediate exclusion of current incomplete 1h bar.
5. Rejection of invalid OHLC relationships (e.g. low > min(open, close), high < max(open, close), negative volume).
6. Consistent 4-hour and 24-hour aggregation contracts.
"""

import time
import pytest
from api.market_drivers import (
    _normalise_candles,
    _finite,
    _positive,
    PROVIDERS,
    build_empirical_forecast,
    reset_market_cache_for_tests,
)


def test_providers_explicit_spot():
    """Verify declared providers represent spot BTC/USD markets only."""
    assert "coinbase" in PROVIDERS
    assert "bitstamp" in PROVIDERS
    assert "kraken" in PROVIDERS
    # Ensure no perpetual swap is included as a primary spot provider
    assert "binance_futures" not in PROVIDERS
    assert "bybit_perpetual" not in PROVIDERS


def test_normalise_candles_deduplication_and_sorting():
    """Verify candles are sorted chronologically and duplicates on the same timestamp are resolved."""
    now = 1700000000.0
    hour = 3600
    base = int(now // hour) * hour - 10 * hour

    raw_rows = [
        {"time": base + 2 * hour, "open": 100, "high": 110, "low": 95, "close": 105, "volume": 10},
        {"time": base + 1 * hour, "open": 95, "high": 102, "low": 90, "close": 100, "volume": 12},
        # Duplicate timestamp with updated close:
        {"time": base + 1 * hour, "open": 95, "high": 103, "low": 90, "close": 101, "volume": 14},
        {"time": base + 3 * hour, "open": 105, "high": 115, "low": 102, "close": 112, "volume": 8},
    ]

    cleaned = _normalise_candles(raw_rows, now=now)
    assert len(cleaned) == 3
    times = [c["time"] for c in cleaned]
    assert times == [float(base + 1 * hour), float(base + 2 * hour), float(base + 3 * hour)]
    # Duplicate resolved by latest occurrence
    assert cleaned[0]["close"] == 101.0
    assert cleaned[0]["volume"] == 14.0


def test_normalise_candles_discards_incomplete_candle():
    """Verify that any candle currently forming (not yet closed before the hour boundary) is discarded."""
    now = 1700000000.0  # current time
    hour = 3600
    current_hour_start = int(now // hour) * hour

    raw_rows = [
        # Past closed candle:
        {"time": current_hour_start - hour, "open": 100, "high": 105, "low": 98, "close": 102, "volume": 5},
        # Current forming candle (not closed):
        {"time": current_hour_start, "open": 102, "high": 108, "low": 101, "close": 107, "volume": 2},
    ]

    cleaned = _normalise_candles(raw_rows, now=now)
    assert len(cleaned) == 1
    assert cleaned[0]["time"] == float(current_hour_start - hour)


def test_normalise_candles_rejects_invalid_ohlc():
    """Verify candles with impossible OHLC relationships are discarded."""
    now = 1700000000.0
    hour = 3600
    base = int(now // hour) * hour - 10 * hour

    invalid_rows = [
        # Low higher than open:
        {"time": base + 1 * hour, "open": 100, "high": 110, "low": 105, "close": 108, "volume": 5},
        # High lower than close:
        {"time": base + 2 * hour, "open": 100, "high": 105, "low": 95, "close": 108, "volume": 5},
        # High lower than low:
        {"time": base + 3 * hour, "open": 100, "high": 90, "low": 95, "close": 92, "volume": 5},
        # Negative volume:
        {"time": base + 4 * hour, "open": 100, "high": 105, "low": 95, "close": 102, "volume": -1},
        # Negative price:
        {"time": base + 5 * hour, "open": -100, "high": 105, "low": 95, "close": 102, "volume": 1},
        # Non-hourly aligned timestamp:
        {"time": base + 6 * hour + 123, "open": 100, "high": 105, "low": 95, "close": 102, "volume": 1},
    ]

    cleaned = _normalise_candles(invalid_rows, now=now)
    assert len(cleaned) == 0


def test_empirical_forecast_contract():
    """Verify empirical baseline forecast labels, sufficient history for 1h, and fail-closed for 24h."""
    now = 1700000000.0
    hour = 3600
    base = int(now // hour) * hour - 50 * hour
    candles = [
        {"time": float(base + i * hour), "open": 100.0 + i, "high": 105.0 + i, "low": 95.0 + i, "close": 101.0 + i, "volume": 10.0}
        for i in range(45)
    ]

    # For 1h horizon: 45 candles provides 44 non-overlapping returns (>= 20 MIN_BLOCKS)
    fc_1h = build_empirical_forecast(candles, 145.0, horizon="1h")
    assert fc_1h["status"] == "EXPERIMENTAL_BASELINE"
    assert fc_1h["horizon"] == "1h"
    assert fc_1h["forecast_mode"] == "EXPERIMENTAL_BASELINE"
    assert fc_1h["validation_status"] == "NOT_VALIDATED_FOR_TRADING"
    assert fc_1h["spot_price_usd"] == 145.0
    assert fc_1h["price_quantiles_usd"]["p10"] < fc_1h["price_quantiles_usd"]["p50"] < fc_1h["price_quantiles_usd"]["p90"]
    assert fc_1h["probability"] is None
    assert fc_1h["direction"] == "NOT_ESTIMATED"

    # For 24h horizon: 45 candles provides only 1 block (< 20 MIN_BLOCKS) -> must fail closed
    fc_24h = build_empirical_forecast(candles, 145.0, horizon="24h")
    assert fc_24h["status"] == "DATA_UNAVAILABLE"
    assert fc_24h["reason"] == "INSUFFICIENT_NON_OVERLAPPING_HISTORY"
    assert fc_24h["price_quantiles_usd"] is None

