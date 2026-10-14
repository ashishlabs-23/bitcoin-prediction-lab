import asyncio
import sqlite3

import pandas as pd

from api import routes_market, routes_prediction


def test_candles_do_not_fabricate_rows_when_cache_is_empty(monkeypatch):
    monkeypatch.setattr(
        routes_market.feature_cache,
        "get_features_df",
        lambda: pd.DataFrame(),
    )

    result = routes_market.get_candles(interval="1h", limit=150)

    assert result["candles"] == []
    assert result["count"] == 0
    assert result["source"] == "feature_cache"
    assert result["degraded"] is True


def test_candles_skip_rows_without_valid_timestamp_and_ohlcv(monkeypatch):
    frame = pd.DataFrame(
        [
            {
                "timestamp": "2026-10-12T12:00:00Z",
                "open": 100.0,
                "high": 105.0,
                "low": 95.0,
                "close": 102.0,
                "volume": 2.0,
            },
            {
                "timestamp": None,
                "open": 100.0,
                "high": 105.0,
                "low": 95.0,
                "close": 102.0,
                "volume": 2.0,
            },
            {
                "timestamp": "2026-10-12T13:00:00Z",
                "open": 100.0,
                "high": 99.0,
                "low": 95.0,
                "close": 102.0,
                "volume": 2.0,
            },
        ]
    )
    monkeypatch.setattr(
        routes_market.feature_cache,
        "get_features_df",
        lambda: frame,
    )

    result = routes_market.get_candles(interval="1h", limit=150)

    assert result["count"] == 1
    assert result["candles"] == [
        {
            "time": 1791806400,
            "open": 100.0,
            "high": 105.0,
            "low": 95.0,
            "close": 102.0,
            "volume": 2.0,
        }
    ]


def test_candles_reject_unsupported_intervals_without_reading_cache(monkeypatch):
    def fail_if_cache_is_read():
        raise AssertionError("unsupported intervals must not read cached candles")

    monkeypatch.setattr(
        routes_market.feature_cache,
        "get_features_df",
        fail_if_cache_is_read,
    )

    result = routes_market.get_candles(interval="5m")

    assert result["status"] == "UNSUPPORTED_REQUEST"
    assert result["candles"] == []
    assert result["count"] == 0


def test_unverified_forecasts_and_explanations_remain_unavailable():
    range_payload = asyncio.run(routes_prediction.get_prediction_range_path())
    counterfactuals = asyncio.run(routes_prediction.get_prediction_counterfactual())
    regime = asyncio.run(routes_prediction.get_market_regime(live=True))
    explanation = asyncio.run(routes_prediction.get_explainability(live=True))
    quality = asyncio.run(routes_prediction.get_signal_quality(live=True))

    assert range_payload["status"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert range_payload["forecast"] is None
    assert range_payload["path"] == []
    assert counterfactuals["status"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert counterfactuals["scenarios"] == []
    assert regime["status"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert regime["current_regime"] is None
    assert explanation["status"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert explanation["top_5_indicators"] == []
    assert quality["status"] == "BLOCKED_PROVENANCE_UNVERIFIED"
    assert quality["score"] is None


def test_prediction_range_history_uses_existing_schema_columns(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE range_forecasts "
        "(forecast_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, current_price REAL NOT NULL)"
    )
    connection.executemany(
        "INSERT INTO range_forecasts VALUES (?, ?, ?)",
        [
            ("older", "2026-10-11T00:00:00Z", 100.0),
            ("newer", "2026-10-12T00:00:00Z", 101.0),
        ],
    )
    monkeypatch.setattr("backtest.market_memory._get_db", lambda: connection)

    result = routes_prediction.get_prediction_range_history(limit=1)

    assert result["status"] == "AVAILABLE"
    assert result["count"] == 1
    assert result["forecasts"][0]["forecast_id"] == "newer"
