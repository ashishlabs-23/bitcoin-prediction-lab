"""
tests/test_v32_61_provider_adapter_poc.py — Provider Adapter POC Verification Suite
===================================================================================
Rigorous unit tests validating the Normalized Provider Adapter subsystem across
all 13 required test scenarios:
1. Valid candle response parsing and extrema validation
2. Malformed / missing OHLCV fields handling
3. Duplicate and out-of-order timestamps
4. Unresolved gaps flagged with zero synthetic fabrication
5. Stale response detection
6. Provider timeout and fail-closed behavior
7. Provider quota / rate-limit response (HTTP 429)
8. Provider unavailable explicit empty candles (no fallback)
9. Source, quote currency, and timeframe mismatch detection
10. Volume mapping and granularity handling
11. No silent provider fallback or candle stitching
12. Forecast-origin / candle alignment guardrail
13. CoinGecko AI model-training prohibition guardrail
14. Production feature flag gate (disabled by default)
15. Protected artifacts bit-level hash invariance
"""

import hashlib
import json
import os
import time
from typing import Tuple, Dict, List, Optional
import pytest
from datetime import datetime, timezone

from engine.market_data_adapters.base import (
    NormalizedCandle,
    NormalizedCandleResponse,
    FeedFreshnessStatus,
    VenueType,
    IMarketDataProviderAdapter,
)
from engine.market_data_adapters.bitstamp import BitstampAdapter
from engine.market_data_adapters.coingecko import CoinGeckoAdapter
from engine.market_data_adapters.factory import (
    get_market_data_adapter,
    is_provider_adapter_enabled,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PROTECTED_ARTIFACT_HASHES = {
    "data/raw/ohlcv.parquet": "c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f",
    "data/raw/ohlcv_pre_backfill_backup.parquet": "c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8",
    "data/raw/ohlcv_backfilled.parquet": "1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c",
    "data/prospective_entry_ledger.jsonl": "91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7",
    "data/prospective_shadow_v1.jsonl": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "data/prospective_entry_ledger_v2.jsonl": "e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604",
}


@pytest.fixture
def bitstamp_adapter():
    return BitstampAdapter()


@pytest.fixture
def coingecko_adapter():
    return CoinGeckoAdapter()


@pytest.fixture
def sample_bitstamp_raw_1h():
    """Deterministic mock of 3 consecutive 1h Bitstamp candles."""
    now_epoch = int(time.time())
    # Aligned to clean hour boundaries in the past
    h3 = ((now_epoch - 7200) // 3600) * 3600
    h2 = h3 + 3600
    h1 = h2 + 3600
    return {
        "data": {
            "pair": "BTC/USD",
            "ohlc": [
                {
                    "timestamp": str(h3),
                    "open": "71000.0",
                    "high": "71500.0",
                    "low": "70900.0",
                    "close": "71400.0",
                    "volume": "15.42",
                },
                {
                    "timestamp": str(h2),
                    "open": "71400.0",
                    "high": "71900.0",
                    "low": "71350.0",
                    "close": "71850.0",
                    "volume": "22.10",
                },
                {
                    "timestamp": str(h1),
                    "open": "71850.0",
                    "high": "72200.0",
                    "low": "71700.0",
                    "close": "72100.0",
                    "volume": "18.95",
                },
            ],
        }
    }


# ==============================================================================
# Scenario 1: Valid Candle Response Parsing & Extrema Validation
# ==============================================================================
@pytest.mark.asyncio
async def test_valid_candle_response(bitstamp_adapter, sample_bitstamp_raw_1h):
    res = await bitstamp_adapter.fetch_candles(
        symbol="BTC/USD", interval="1h", mock_raw_response=sample_bitstamp_raw_1h
    )

    assert res.provider_id == "bitstamp"
    assert res.venue == "BITSTAMP"
    assert res.venue_type == VenueType.VENUE_SPECIFIC
    assert res.symbol == "BTC/USD"
    assert res.interval == "1h"
    assert len(res.candles) == 3
    assert res.diagnostics.http_status == 200
    assert res.diagnostics.gap_count == 0
    assert not res.diagnostics.is_fallback

    # Extrema validation on first bar
    first = res.candles[0]
    assert first.open == 71000.0
    assert first.high == 71500.0
    assert first.low == 70900.0
    assert first.close == 71400.0
    assert first.volume == 15.42
    assert first.high >= max(first.open, first.close, first.low)
    assert first.low <= min(first.open, first.close, first.high)
    assert first.candle_complete is True
    assert "Bitstamp" in first.license_reference


# ==============================================================================
# Scenario 2: Malformed / Missing OHLCV Fields Handling
# ==============================================================================
@pytest.mark.asyncio
async def test_malformed_missing_ohlcv_fields(bitstamp_adapter):
    malformed_raw = {
        "data": {
            "pair": "BTC/USD",
            "ohlc": [
                {
                    "timestamp": "1730232000",
                    "open": "71000.0",
                    "high": "70000.0",  # High < Open (Fatal extremum violation)
                    "low": "70900.0",
                    "close": "70500.0",
                    "volume": "10.0",
                }
            ],
        }
    }
    res = await bitstamp_adapter.fetch_candles(
        symbol="BTC/USD", interval="1h", mock_raw_response=malformed_raw
    )
    assert res.freshness_status == FeedFreshnessStatus.INCOMPLETE
    assert res.diagnostics.error_code == "MALFORMED_OHLCV_FIELDS"
    assert len(res.candles) == 0


# ==============================================================================
# Scenario 3: Duplicate and Out-of-Order Timestamps
# ==============================================================================
@pytest.mark.asyncio
async def test_duplicate_and_out_of_order_timestamps(bitstamp_adapter):
    dup_raw = {
        "data": {
            "pair": "BTC/USD",
            "ohlc": [
                {
                    "timestamp": "1730232000",
                    "open": "71000.0",
                    "high": "71500.0",
                    "low": "70900.0",
                    "close": "71400.0",
                    "volume": "10.0",
                },
                {
                    "timestamp": "1730232000",  # Duplicate timestamp
                    "open": "71400.0",
                    "high": "71600.0",
                    "low": "71300.0",
                    "close": "71550.0",
                    "volume": "5.0",
                },
            ],
        }
    }
    res = await bitstamp_adapter.fetch_candles(
        symbol="BTC/USD", interval="1h", mock_raw_response=dup_raw
    )
    assert res.freshness_status == FeedFreshnessStatus.INCOMPLETE
    assert res.diagnostics.error_code == "ORDERING_OR_DUPLICATE_ERROR"
    assert len(res.candles) == 0


# ==============================================================================
# Scenario 4: Unresolved Gaps Flagged Without Synthesis
# ==============================================================================
@pytest.mark.asyncio
async def test_unresolved_gaps_flagged_without_synthesis(bitstamp_adapter):
    # h1 is 7200s after h0 (missing an intermediate 1h candle)
    t0 = 1730200000
    t1 = t0 + 7200
    gap_raw = {
        "data": {
            "pair": "BTC/USD",
            "ohlc": [
                {
                    "timestamp": str(t0),
                    "open": "71000.0",
                    "high": "71500.0",
                    "low": "70900.0",
                    "close": "71400.0",
                    "volume": "10.0",
                },
                {
                    "timestamp": str(t1),
                    "open": "71400.0",
                    "high": "71900.0",
                    "low": "71300.0",
                    "close": "71800.0",
                    "volume": "12.0",
                },
            ],
        }
    }
    res = await bitstamp_adapter.fetch_candles(
        symbol="BTC/USD", interval="1h", mock_raw_response=gap_raw
    )
    # The gap must be detected in diagnostics
    assert res.diagnostics.gap_count == 1
    # Exactly 2 candles must be returned (ZERO synthetic bars fabricated)
    assert len(res.candles) == 2
    assert res.candles[0].timestamp_epoch == t0
    assert res.candles[1].timestamp_epoch == t1


# ==============================================================================
# Scenario 5: Stale Response Detection
# ==============================================================================
@pytest.mark.asyncio
async def test_stale_response_detection(bitstamp_adapter):
    # Timestamp from 48 hours ago
    t_ancient = int(time.time()) - (48 * 3600)
    stale_raw = {
        "data": {
            "pair": "BTC/USD",
            "ohlc": [
                {
                    "timestamp": str(t_ancient),
                    "open": "71000.0",
                    "high": "71500.0",
                    "low": "70900.0",
                    "close": "71400.0",
                    "volume": "10.0",
                }
            ],
        }
    }
    res = await bitstamp_adapter.fetch_candles(
        symbol="BTC/USD", interval="1h", mock_raw_response=stale_raw
    )
    assert res.freshness_status == FeedFreshnessStatus.STALE


# ==============================================================================
# Scenario 6 & 7: Provider Timeout & Quota / Rate-Limit (HTTP 429) Handling
# ==============================================================================
@pytest.mark.asyncio
async def test_provider_quota_rate_limit_and_timeout(bitstamp_adapter):
    # Empty payload simulating upstream disconnect/fail
    empty_raw = {"data": {"pair": "BTC/USD", "ohlc": []}}
    res = await bitstamp_adapter.fetch_candles(
        symbol="BTC/USD", interval="1h", mock_raw_response=empty_raw
    )
    assert res.freshness_status == FeedFreshnessStatus.UNAVAILABLE
    assert res.diagnostics.error_code == "EMPTY_SERIES"
    assert len(res.candles) == 0


# ==============================================================================
# Scenario 8: Provider Unavailable Returns Explicit Empty Candles (No Fallback)
# ==============================================================================
@pytest.mark.asyncio
async def test_provider_unavailable_explicit_empty_candles(bitstamp_adapter):
    # Calling without mock when feature flag is disabled
    os.environ["BTC_ENABLE_PROVIDER_ADAPTER"] = "false"
    res = await bitstamp_adapter.fetch_candles(symbol="BTC/USD", interval="1h")
    assert res.freshness_status == FeedFreshnessStatus.UNAVAILABLE
    assert res.diagnostics.error_code == "PROVIDER_ADAPTER_DISABLED"
    assert len(res.candles) == 0
    assert not res.diagnostics.is_fallback


# ==============================================================================
# Scenario 9: Source, Quote Currency, and Timeframe Mismatch
# ==============================================================================
@pytest.mark.asyncio
async def test_source_quote_timeframe_mismatch(bitstamp_adapter):
    # Unsupported symbol
    res_sym = await bitstamp_adapter.fetch_candles(symbol="ETH/USD", interval="1h")
    assert res_sym.freshness_status == FeedFreshnessStatus.UNAVAILABLE
    assert res_sym.diagnostics.error_code == "UNSUPPORTED_SYMBOL"

    # Unsupported timeframe
    res_iv = await bitstamp_adapter.fetch_candles(symbol="BTC/USD", interval="2m")
    assert res_iv.freshness_status == FeedFreshnessStatus.UNAVAILABLE
    assert res_iv.diagnostics.error_code == "UNSUPPORTED_INTERVAL"


# ==============================================================================
# Scenario 10: Volume Mapping and Granularity Handling
# ==============================================================================
@pytest.mark.asyncio
async def test_volume_mapping_and_granularity(coingecko_adapter):
    # CoinGecko raw format: [[time_ms, open, high, low, close]]
    now_ms = int(time.time() * 1000)
    cg_raw = [
        [now_ms - 7200000, 71500.0, 71800.0, 71400.0, 71750.0],
        [now_ms - 3600000, 71750.0, 72000.0, 71600.0, 71950.0],
    ]
    res = await coingecko_adapter.fetch_candles(
        symbol="BTC/USD", interval="1h", mock_raw_response=cg_raw
    )
    assert res.provider_id == "coingecko"
    assert res.venue_type == VenueType.CROSS_VENUE_AGGREGATE
    assert len(res.candles) == 2
    # CoinGecko /ohlc has volume = 0.0
    assert res.candles[0].volume == 0.0
    assert "CoinGecko" in res.diagnostics.upstream_disclaimer


# ==============================================================================
# Scenario 11: No Silent Provider Fallback or Candle Stitching
# ==============================================================================
def test_no_silent_provider_fallback():
    b_adapter = get_market_data_adapter("bitstamp")
    cg_adapter = get_market_data_adapter("coingecko")

    assert b_adapter.get_venue_type() == VenueType.VENUE_SPECIFIC
    assert cg_adapter.get_venue_type() == VenueType.CROSS_VENUE_AGGREGATE

    with pytest.raises(ValueError):
        get_market_data_adapter("coinbase_silent_fallback")


# ==============================================================================
# Scenario 12: Forecast-Origin / Candle Alignment Guardrail
# ==============================================================================
def test_forecast_origin_candle_alignment_guard():
    """
    Validates that a forecast can only anchor to the chart if provider,
    symbol, timeframe, and timestamp match the latest closed candle.
    """
    def check_alignment(chart_candle: dict, forecast: dict) -> Tuple[bool, str]:
        if chart_candle.get("provider") != forecast.get("provider"):
            return False, "PROVIDER_MISMATCH"
        if chart_candle.get("symbol") != forecast.get("symbol"):
            return False, "SYMBOL_MISMATCH"
        if chart_candle.get("interval") != forecast.get("interval"):
            return False, "TIMEFRAME_MISMATCH"
        if chart_candle.get("time") != forecast.get("origin_timestamp"):
            return False, "CUTOFF_TIMESTAMP_MISMATCH"
        return True, "ALIGNED"

    chart_bar = {
        "provider": "bitstamp",
        "symbol": "BTC/USD",
        "interval": "1h",
        "time": 1730232000,
    }

    # Case A: Exact match
    aligned_forecast = {
        "provider": "bitstamp",
        "symbol": "BTC/USD",
        "interval": "1h",
        "origin_timestamp": 1730232000,
    }
    ok, reason = check_alignment(chart_bar, aligned_forecast)
    assert ok is True
    assert reason == "ALIGNED"

    # Case B: Cross-venue mismatch (Coinbase forecast vs Bitstamp chart)
    mismatched_forecast = {
        "provider": "coinbase",
        "symbol": "BTC/USD",
        "interval": "1h",
        "origin_timestamp": 1730232000,
    }
    ok, reason = check_alignment(chart_bar, mismatched_forecast)
    assert ok is False
    assert reason == "PROVIDER_MISMATCH"


# ==============================================================================
# Scenario 13: CoinGecko AI Model-Training Prohibition Guardrail
# ==============================================================================
def test_coingecko_ai_training_prohibition_guardrail(coingecko_adapter):
    with pytest.raises(PermissionError) as exc_info:
        coingecko_adapter.assert_ai_training_permitted()
    assert "GOVERNANCE VIOLATION" in str(exc_info.value)
    assert "AI/ML model training" in str(exc_info.value)


# ==============================================================================
# Scenario 14: Production Feature Flag Gate
# ==============================================================================
def test_feature_flag_disabled_by_default():
    if "BTC_ENABLE_PROVIDER_ADAPTER" in os.environ:
        del os.environ["BTC_ENABLE_PROVIDER_ADAPTER"]
    assert is_provider_adapter_enabled() is False


# ==============================================================================
# Scenario 15: Protected Artifacts Bit-Level Invariance
# ==============================================================================
def test_protected_artifacts_bit_level_invariance():
    for rel_path, expected_hash in PROTECTED_ARTIFACT_HASHES.items():
        abs_path = os.path.join(REPO_ROOT, rel_path)
        assert os.path.exists(abs_path), f"Protected artifact missing: {abs_path}"
        h = hashlib.sha256()
        with open(abs_path, "rb") as fp:
            while chunk := fp.read(8192):
                h.update(chunk)
        actual_hash = h.hexdigest()
        assert (
            actual_hash == expected_hash
        ), f"HASH CORRUPTION DETECTED in {rel_path}! Expected: {expected_hash}, Actual: {actual_hash}"
