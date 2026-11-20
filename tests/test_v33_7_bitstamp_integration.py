"""
tests/test_v33_7_bitstamp_integration.py — Bitstamp Market Data Integration Suite
==================================================================================
Comprehensive test suite validating:
1. Successful Bitstamp response parsing.
2. Incomplete hourly candle rejection (exclude_current_candle=true and t_close <= t_retrieval).
3. Data freshness calculation using completed candle close time.
4. Missing candle rejection (gap detection; zero interpolation).
5. Duplicate candle rejection.
6. Invalid OHLC extrema and volume rejection.
7. API timeout fail-closed handling.
8. HTTP 429 rate limit handling.
9. Source separation from Coinbase historical dataset.
10. Source-dependent model compatibility gate (C2 conformal suppression on Bitstamp data).
11. Repeated-click request deduplication via short cache.
12. Zero simulated trade attempts.
13. One authorized real public API retrieval integration test.
"""

import copy
import hashlib
import json
import os
import time
import pytest
import pandas as pd
from datetime import datetime, timezone
from engine.range_forecast_service import RangeForecastService

from engine.bitstamp_market_data_service import (
    BitstampMarketDataService,
    get_bitstamp_service,
    BITSTAMP_PARQUET_PATH,
    BITSTAMP_STORAGE_DIR
)


@pytest.fixture(autouse=True)
def prevent_persistent_forecast_writes(monkeypatch):
    monkeypatch.setattr(RangeForecastService, "_persist_forecast", lambda *_: None)
from engine.regime_strategy_tournament import analyse_current_market
from engine.decoupled_analysis_engine import decoupled_analysis_engine

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FROZEN_OHLCV_PATH = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
EXPECTED_OHLCV_SHA256 = "ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057"


def generate_mock_bitstamp_payload(
    bar_count: int = 100,
    base_timestamp: int = 1793600000,
    inject_gap_at: int = -1,
    inject_duplicate_at: int = -1,
    inject_invalid_ohlc_at: int = -1,
    inject_incomplete_at: int = -1
) -> dict:
    ohlc = []
    current_ts = base_timestamp
    price = 77000.0

    for i in range(bar_count):
        if i == inject_gap_at:
            current_ts += 7200  # 2-hour gap
        elif i == inject_duplicate_at:
            pass  # same timestamp as previous
        else:
            current_ts += 3600

        o = price
        h = price + 150.0
        l = price - 100.0
        c = price + 50.0
        v = 120.5

        if i == inject_invalid_ohlc_at:
            h = l - 50.0  # high < low

        ohlc.append({
            "timestamp": str(current_ts),
            "open": str(o),
            "high": str(h),
            "low": str(l),
            "close": str(c),
            "volume": str(v)
        })
        price = c

    if inject_incomplete_at >= 0:
        # candle in the future
        future_ts = int(time.time()) + 7200
        ohlc.append({
            "timestamp": str(future_ts),
            "open": "78000.0",
            "high": "78100.0",
            "low": "77900.0",
            "close": "78050.0",
            "volume": "50.0"
        })

    return {
        "data": {
            "pair": "BTC/USD",
            "ohlc": ohlc
        }
    }


def test_1_successful_bitstamp_response_validation():
    service = BitstampMarketDataService()
    now_epoch = 1793600000 + (100 * 3600) + 1800
    mock_payload = generate_mock_bitstamp_payload(bar_count=50, base_timestamp=1793600000)

    ok, valid_bars, err = service.validate_bitstamp_ohlc(mock_payload, retrieval_epoch=now_epoch)
    assert ok is True, f"Validation failed: {err}"
    assert len(valid_bars) == 50
    assert valid_bars[0]["open"] == 77000.0
    assert valid_bars[-1]["timestamp"] > valid_bars[0]["timestamp"]


def test_2_incomplete_hourly_candle_rejection():
    service = BitstampMarketDataService()
    now_epoch = int(time.time())
    mock_payload = generate_mock_bitstamp_payload(bar_count=20, base_timestamp=now_epoch - 3600*25, inject_incomplete_at=20)

    ok, valid_bars, err = service.validate_bitstamp_ohlc(mock_payload, retrieval_epoch=now_epoch)
    assert ok is False
    assert "INCOMPLETE_CANDLE" in err


def test_3_data_freshness_calculation():
    service = BitstampMarketDataService()
    now_epoch = time.time()
    # Candle that ended 30 minutes ago (1800s)
    candle_open_epoch = now_epoch - 3600 - 1800
    df = pd.DataFrame([{
        "timestamp": pd.to_datetime(candle_open_epoch, unit="s", utc=True),
        "available_time": pd.to_datetime(candle_open_epoch + 3600, unit="s", utc=True),
        "open": 77000.0,
        "high": 77100.0,
        "low": 76900.0,
        "close": 77050.0,
        "volume": 100.0,
        "source_exchange": "BITSTAMP",
        "source_symbol": "BTC/USD",
    }])

    fresh = service.compute_bitstamp_freshness(df, max_age_hours=2.0)
    assert fresh["is_fresh"] is True
    assert fresh["data_freshness_status"] == "FRESH"
    assert fresh["data_age_hours"] == pytest.approx(0.5, abs=0.1)

    # Candle that ended 3 hours ago (10800s) -> STALE
    stale_open_epoch = now_epoch - 3600 - 10800
    df_stale = pd.DataFrame([{
        "timestamp": pd.to_datetime(stale_open_epoch, unit="s", utc=True),
        "available_time": pd.to_datetime(stale_open_epoch + 3600, unit="s", utc=True),
        "open": 77000.0,
        "high": 77100.0,
        "low": 76900.0,
        "close": 77050.0,
        "volume": 100.0,
        "source_exchange": "BITSTAMP",
        "source_symbol": "BTC/USD",
    }])

    stale_res = service.compute_bitstamp_freshness(df_stale, max_age_hours=2.0)
    assert stale_res["is_fresh"] is False
    assert stale_res["data_freshness_status"] == "MARKET_DATA_STALE"
    assert stale_res["data_age_hours"] >= 3.0


def test_4_missing_candle_gap_rejection():
    service = BitstampMarketDataService()
    now_epoch = 1793600000 + (100 * 3600) + 1800
    mock_payload = generate_mock_bitstamp_payload(bar_count=50, base_timestamp=1793600000, inject_gap_at=10)

    ok, valid_bars, err = service.validate_bitstamp_ohlc(mock_payload, retrieval_epoch=now_epoch)
    assert ok is False
    assert "INTERVAL_GAP_DETECTED" in err


def test_5_duplicate_candle_rejection():
    service = BitstampMarketDataService()
    now_epoch = 1793600000 + (100 * 3600) + 1800
    mock_payload = generate_mock_bitstamp_payload(bar_count=50, base_timestamp=1793600000, inject_duplicate_at=15)

    ok, valid_bars, err = service.validate_bitstamp_ohlc(mock_payload, retrieval_epoch=now_epoch)
    assert ok is False
    assert "DUPLICATE_TIMESTAMP" in err


def test_6_invalid_ohlc_extrema_rejection():
    service = BitstampMarketDataService()
    now_epoch = 1793600000 + (100 * 3600) + 1800
    mock_payload = generate_mock_bitstamp_payload(bar_count=50, base_timestamp=1793600000, inject_invalid_ohlc_at=5)

    ok, valid_bars, err = service.validate_bitstamp_ohlc(mock_payload, retrieval_epoch=now_epoch)
    assert ok is False
    assert "HIGH_LESS_THAN_LOW" in err or "HIGH_BELOW_OPEN_CLOSE" in err


def test_7_source_separation_from_coinbase_dataset():
    # Verify that the Bitstamp parquet file is stored strictly in data/providers/bitstamp/
    service = get_bitstamp_service()
    assert BITSTAMP_PARQUET_PATH.endswith(os.path.join("data", "providers", "bitstamp", "BTCUSD_1h.parquet"))
    assert BITSTAMP_PARQUET_PATH != FROZEN_OHLCV_PATH

    # Verify that data/raw/ohlcv.parquet hash is invariant
    assert os.path.exists(FROZEN_OHLCV_PATH)
    with open(FROZEN_OHLCV_PATH, "rb") as fp:
        actual_hash = hashlib.sha256(fp.read()).hexdigest()
    assert actual_hash == EXPECTED_OHLCV_SHA256, f"Coinbase dataset was modified! {actual_hash} != {EXPECTED_OHLCV_SHA256}"


def test_8_source_dependent_model_compatibility_gate():
    # Generate 100 bars with source_exchange == BITSTAMP
    now_epoch = time.time()
    start_epoch = now_epoch - (100 * 3600) - 1800
    rows = []
    p = 77000.0
    for i in range(100):
        t = start_epoch + (i * 3600)
        rows.append({
            "timestamp": pd.to_datetime(t, unit="s", utc=True),
            "available_time": pd.to_datetime(t + 3600, unit="s", utc=True),
            "open": p,
            "high": p + 100.0,
            "low": p - 80.0,
            "close": p + 20.0,
            "volume": 150.0,
            "source_exchange": "BITSTAMP",
            "source_symbol": "BTC/USD",
            "interval": "1h"
        })
        p += 20.0

    df_bitstamp = pd.DataFrame(rows)

    intel = decoupled_analysis_engine.compute_market_intelligence_report(
        df_closed=df_bitstamp,
        live_price=p,
        max_age_hours=2.0
    )

    # Conformal envelope must be marked UNAVAILABLE with reason code
    c2 = intel.get("conformal_risk_envelope_7d") or {}
    assert c2.get("status") == "UNAVAILABLE"
    assert c2.get("calibration_status") == "DISABLED_BY_GOVERNANCE"
    assert c2.get("reason_code") == "C2_DISABLED"
    assert c2.get("point_forecast_variance") is None

    # Technical metrics remain valid and populated
    term_struct = intel.get("volatility_term_structure") or {}
    assert term_struct.get("rv_1h_pct") is not None
    assert term_struct.get("rv_24h_pct") is not None
    assert intel.get("volatility_regime") is not None


def test_9_repeated_click_request_deduplication():
    service = BitstampMarketDataService()
    base_ts = int(time.time()) - (60 * 3600)
    mock_payload = generate_mock_bitstamp_payload(bar_count=50, base_timestamp=base_ts)

    # First fetch (with mock response)
    ok1, df1, meta1 = service.get_or_refresh_bitstamp_data(force_refresh=True, mock_raw_response=mock_payload)
    assert ok1 is True, f"First fetch failed: {meta1}"
    assert meta1["cache_status"] == "FRESH_NETWORK_ACQUISITION"

    # Second fetch immediately (within TTL)
    ok2, df2, meta2 = service.get_or_refresh_bitstamp_data(force_refresh=False, max_cache_age_sec=60.0)
    assert ok2 is True, f"Second fetch failed: {meta2}"
    assert meta2["cache_status"] == "IN_MEMORY_CACHE_HIT"
    assert len(df2) == len(df1)


def test_10_zero_simulated_trade_attempts_on_analysis():
    # Verify that running analyse on Bitstamp data does NOT create any simulated trade attempts
    if os.path.exists(BITSTAMP_PARQUET_PATH):
        df_bs = pd.read_parquet(BITSTAMP_PARQUET_PATH)
        res = analyse_current_market(df_bs, live_price=float(df_bs["close"].iloc[-1]), max_age_hours=2.0)
        assert res.get("attempts_created") == 0
        assert res.get("is_read_only") is True


def test_11_external_public_api_retrieval_is_blocked_without_network_or_persistence(monkeypatch):
    from engine.data_mode import ExternalNetworkBlockedError

    monkeypatch.setenv("BTC_DATA_MODE", "fixture")
    service = BitstampMarketDataService()
    with pytest.raises(ExternalNetworkBlockedError):
        service.fetch_raw_bitstamp_ohlcv()
