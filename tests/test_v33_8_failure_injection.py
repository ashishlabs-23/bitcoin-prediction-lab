from fastapi import HTTPException
"""
tests/test_v33_8_failure_injection.py — Exhaustive Failure-Injection & Invariant Testing Suite
=============================================================================================
Validates fail-closed behavior across all required failure injection modes:
1. HTTP Timeout
2. HTTP 429 Rate Limit
3. Invalid / Malformed JSON
4. Empty response (Missing data)
5. Duplicate candle timestamps
6. Interval gaps (Missing hourly candles)
7. Invalid OHLC extrema (high < low, high < open, low > close)
8. Stale market data (> 2.0 hours)
9. Upstream provider network failure
10. Rapid repeated clicks and cache deduplication
11. Fail-closed without mutating or losing last valid historical snapshot
"""

import copy
import hashlib
import json
import os
import time
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from engine.bitstamp_market_data_service import (
    BitstampMarketDataService,
    BITSTAMP_PARQUET_PATH,
    BITSTAMP_STORAGE_DIR
)
from engine.regime_strategy_tournament import analyse_current_market, check_data_freshness_and_gaps
from engine.htf_setup_detector import HTFSetupDetector

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FROZEN_OHLCV_PATH = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
EXPECTED_OHLCV_SHA256 = "ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057"


def make_valid_ohlc_payload(n=25, base_ts=1793600000):
    ohlc = []
    ts = base_ts
    price = 77000.0
    for _ in range(n):
        ohlc.append({
            "timestamp": str(ts),
            "open": str(price),
            "high": str(price + 100.0),
            "low": str(price - 100.0),
            "close": str(price + 20.0),
            "volume": "10.5"
        })
        price += 20.0
        ts += 3600
    return {"data": {"pair": "BTC/USD", "ohlc": ohlc}}


def test_failure_1_http_timeout():
    svc = BitstampMarketDataService()
    with patch.object(svc, "fetch_raw_bitstamp_ohlcv", return_value=(False, None, "UPSTREAM_TIMEOUT: exceeded 15s", 15000.0, "")):
        ok, df, meta = svc.get_or_refresh_bitstamp_data(force_refresh=True, persist=False)
        assert ok is False
        assert df is None
        assert "TIMEOUT" in meta["error_message"]
        assert meta["error_code"] == "MARKET_DATA_UNAVAILABLE"


def test_failure_2_http_429_rate_limit():
    svc = BitstampMarketDataService()
    with patch.object(svc, "fetch_raw_bitstamp_ohlcv", return_value=(False, None, "RATE_LIMIT_EXCEEDED: Bitstamp HTTP 429", 120.0, "")):
        ok, df, meta = svc.get_or_refresh_bitstamp_data(force_refresh=True, persist=False)
        assert ok is False
        assert df is None
        assert "RATE_LIMIT" in meta["error_message"]
        assert meta["error_code"] == "MARKET_DATA_UNAVAILABLE"


def test_failure_3_malformed_json():
    svc = BitstampMarketDataService()
    # Response is not dict or missing data/ohlc
    malformed = {"corrupted_field": 12345}
    ok, valid_bars, err = svc.validate_bitstamp_ohlc(malformed, retrieval_epoch=1793600000)
    assert ok is False
    assert "EMPTY_OR_MISSING_OHLC" in err


def test_failure_4_empty_response():
    svc = BitstampMarketDataService()
    empty = {"data": {"pair": "BTC/USD", "ohlc": []}}
    ok, valid_bars, err = svc.validate_bitstamp_ohlc(empty, retrieval_epoch=1793600000)
    assert ok is False
    assert "EMPTY_OR_MISSING_OHLC" in err


def test_failure_5_duplicate_candles():
    svc = BitstampMarketDataService()
    payload = make_valid_ohlc_payload(n=10)
    # Duplicate candle 4
    payload["data"]["ohlc"][5]["timestamp"] = payload["data"]["ohlc"][4]["timestamp"]
    ok, valid_bars, err = svc.validate_bitstamp_ohlc(payload, retrieval_epoch=1793600000 + 3600*20)
    assert ok is False
    assert "DUPLICATE_TIMESTAMP" in err or "MONOTONIC" in err


def test_failure_6_missing_candle_gap():
    svc = BitstampMarketDataService()
    payload = make_valid_ohlc_payload(n=10)
    # Inject 2-hour gap between candle 4 and 5
    payload["data"]["ohlc"][5]["timestamp"] = str(int(payload["data"]["ohlc"][4]["timestamp"]) + 7200)
    ok, valid_bars, err = svc.validate_bitstamp_ohlc(payload, retrieval_epoch=1793600000 + 3600*20)
    assert ok is False
    assert "INTERVAL_GAP" in err


def test_failure_7_invalid_ohlc_extrema():
    svc = BitstampMarketDataService()
    # Case A: High < Low
    payload_a = make_valid_ohlc_payload(n=5)
    payload_a["data"]["ohlc"][2]["high"] = "76500.0"
    payload_a["data"]["ohlc"][2]["low"] = "77000.0"
    ok_a, _, err_a = svc.validate_bitstamp_ohlc(payload_a, retrieval_epoch=1793600000 + 3600*20)
    assert ok_a is False
    assert "HIGH" in err_a or "LOW" in err_a

    # Case B: High < Open
    payload_b = make_valid_ohlc_payload(n=5)
    payload_b["data"]["ohlc"][2]["open"] = "78000.0"
    payload_b["data"]["ohlc"][2]["high"] = "77500.0"
    ok_b, _, err_b = svc.validate_bitstamp_ohlc(payload_b, retrieval_epoch=1793600000 + 3600*20)
    assert ok_b is False
    assert "HIGH_BELOW_OPEN_CLOSE" in err_b


def test_failure_8_stale_response_fail_closed():
    # Construct a dataset of 100 bars ending 4 hours ago
    now_epoch = time.time()
    stale_ts = now_epoch - (100 * 3600) - 3600*4
    rows = []
    p = 77000.0
    for i in range(100):
        t = stale_ts + (i * 3600)
        rows.append({
            "timestamp": pd.to_datetime(t, unit="s", utc=True),
            "available_time": pd.to_datetime(t + 3600, unit="s", utc=True),
            "open": p,
            "high": p + 100.0,
            "low": p - 80.0,
            "close": p + 20.0,
            "volume": 100.0,
            "source_exchange": "BITSTAMP",
            "source_symbol": "BTC/USD"
        })
        p += 20.0
    df_stale = pd.DataFrame(rows)

    fresh_info = check_data_freshness_and_gaps(df_stale, max_age_hours=2.0)
    assert fresh_info["is_fresh"] is False
    assert fresh_info["freshness_status"] == "MARKET_DATA_STALE"
    assert fresh_info["observed_age_seconds"] >= 3600.0 * 3.5

    detector = HTFSetupDetector()
    res = detector.detect_setup(
        df_1h=df_stale,
        observed_regime="VOLATILITY_EXPANSION",
        is_data_stale=True,
        observed_age_hours=fresh_info["observed_age_seconds"] / 3600.0,
        enforce_stale_blocking=True
    )
    assert res["setup_status"] == "BLOCKED"
    assert res["data_freshness_status"] == "MARKET_DATA_STALE"
    assert "STALE_MARKET_DATA_BLOCKED" in res["reason_codes"]


def test_failure_9_provider_network_outage_fallback():
    svc = BitstampMarketDataService()
    # Mock complete network outage
    with patch.object(svc, "fetch_raw_bitstamp_ohlcv", return_value=(False, None, "UPSTREAM_FETCH_FAILED: Host unreachable", 2000.0, "")):
        ok, df, meta = svc.get_or_refresh_bitstamp_data(force_refresh=True, persist=False)
        assert ok is False
        assert df is None
        assert meta["error_code"] == "MARKET_DATA_UNAVAILABLE"


def test_failure_10_repeat_clicks_and_cache_deduplication():
    svc = BitstampMarketDataService()
    now_epoch = int(time.time())
    base_ts = now_epoch - (30 * 3600)
    payload = make_valid_ohlc_payload(n=20, base_ts=base_ts)
    # First call with mock
    ok1, df1, meta1 = svc.get_or_refresh_bitstamp_data(force_refresh=True, mock_raw_response=payload, persist=False)
    assert ok1 is True, f"First fetch failed: {meta1}"
    # Immediate repeat call (within 120s TTL)
    ok2, df2, meta2 = svc.get_or_refresh_bitstamp_data(force_refresh=False, max_cache_age_sec=120.0)
    assert ok2 is True, f"Second fetch failed: {meta2}"
    assert meta2["cache_status"] == "IN_MEMORY_CACHE_HIT"


def test_failure_11_fail_closed_without_modifying_historical_snapshot():
    # Verify that data/raw/ohlcv.parquet is completely untouched
    assert os.path.exists(FROZEN_OHLCV_PATH)
    with open(FROZEN_OHLCV_PATH, "rb") as fp:
        actual_hash = hashlib.sha256(fp.read()).hexdigest()
    assert actual_hash == EXPECTED_OHLCV_SHA256


def test_failure_12_tournament_analyse_requires_supplied_snapshot():
    from api.routes_tournament import AnalyseRequestModel, post_analyse_market
    req = AnalyseRequestModel(instrument="BTC-USD", timeframe="1h")
    with pytest.raises(HTTPException) as exc:
        post_analyse_market(req)
    assert exc.value.status_code == 422
    assert exc.value.detail["error_code"] == "DATA_UNAVAILABLE"


def test_failure_13_tournament_analyse_does_not_load_any_dataset_on_missing_snapshot():
    from api.routes_tournament import AnalyseRequestModel, post_analyse_market
    with patch("pandas.read_parquet") as mock_read_parquet:
        req = AnalyseRequestModel(instrument="BTC-USD", timeframe="1h")
        with pytest.raises(HTTPException) as exc:
            post_analyse_market(req)
        assert exc.value.status_code == 422
        mock_read_parquet.assert_not_called()


def test_failure_14_tournament_analyse_rejects_missing_local_snapshot():
    from api.routes_tournament import AnalyseRequestModel, post_analyse_market
    req = AnalyseRequestModel(
        instrument="BTC-USD",
        timeframe="1h",
        data_source="LOCAL_HISTORICAL_SNAPSHOT"
    )
    with pytest.raises(HTTPException) as exc:
        post_analyse_market(req)
    assert exc.value.status_code == 422
    assert exc.value.detail["error_code"] == "DATA_UNAVAILABLE"


def test_failure_15_tournament_analyse_never_fetches_coinbase_substitution():
    from api.routes_tournament import AnalyseRequestModel, post_analyse_market
    with patch.object(
        BitstampMarketDataService,
        "get_or_refresh_bitstamp_data",
        return_value=(False, None, {"error_code": "BITSTAMP_OUTAGE"})
    ) as provider_fetch:
        req = AnalyseRequestModel(instrument="BTC-USD", timeframe="1h")
        with pytest.raises(HTTPException) as exc:
            post_analyse_market(req)
        assert exc.value.status_code == 422
        assert exc.value.detail["error_code"] == "DATA_UNAVAILABLE"
        provider_fetch.assert_not_called()
