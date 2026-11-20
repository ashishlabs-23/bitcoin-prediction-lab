"""Tests for Tardis.dev Trade Archive Parser and Multi-Timeframe Candle Aggregator.

BTCognitive Milestone V35.0 verification suite.
"""

import io
import pytest
import pandas as pd
from engine.market_data_adapters.tardis_sample_parser import TardisSampleParser


def test_tardis_trade_parser_deduplication_and_sorting():
    # Synthetic Tardis CSV snippet with duplicates and out-of-order timestamps
    # Timestamps in microseconds: 1561939200000000 = 2019-07-01 00:00:00 UTC
    raw_csv = """exchange,symbol,timestamp,local_timestamp,id,side,price,amount
bitstamp,BTCUSD,1561939205000000,1561939205001000,102,buy,10510.5,0.25
bitstamp,BTCUSD,1561939200000000,1561939200002000,101,buy,10500.0,0.50
bitstamp,BTCUSD,1561939200000000,1561939200002000,101,buy,10500.0,0.50
bitstamp,BTCUSD,1561939210000000,1561939210001000,103,sell,10495.0,1.20
"""
    df_clean = TardisSampleParser.load_and_clean_trades(raw_csv, symbol_filter="BTCUSD")

    # Verify deduplication: 4 raw lines (with 1 duplicate) -> 3 distinct records
    assert len(df_clean) == 3
    # Verify chronological sorting
    assert df_clean["id"].tolist() == [101, 102, 103]
    assert df_clean["price"].tolist() == [10500.0, 10510.5, 10495.0]
    assert str(df_clean["dt_utc"].iloc[0]) == "2019-07-01 00:00:00+00:00"


def test_tardis_aggregation_5m_and_1h():
    # Generate 1 hour of trade data (e.g. 12 trades, 1 every 5 minutes)
    trades = []
    base_us = 1561939200000000  # 2019-07-01 00:00:00 UTC
    prices = [10000, 10020, 10010, 10050, 10030, 10060, 10040, 10080, 10070, 10090, 10085, 10100]

    for i in range(12):
        ts = base_us + (i * 300 * 1000000)  # + i * 5 minutes in microseconds
        trades.append({
            "exchange": "bitstamp",
            "symbol": "BTCUSD",
            "timestamp": ts,
            "local_timestamp": ts + 1000,
            "id": 1000 + i,
            "side": "buy" if i % 2 == 0 else "sell",
            "price": prices[i],
            "amount": 1.0
        })

    df_trades = pd.DataFrame(trades)
    df_trades["dt_utc"] = pd.to_datetime(df_trades["timestamp"], unit="us", utc=True)

    # Aggregate to 5m
    df_5m = TardisSampleParser.aggregate_to_timeframe(df_trades, freq="5min")
    assert len(df_5m) == 12
    assert df_5m["open"].iloc[0] == 10000.0
    assert df_5m["close"].iloc[-1] == 10100.0

    # Aggregate to 1h
    df_1h = TardisSampleParser.aggregate_to_timeframe(df_trades, freq="1h")
    assert len(df_1h) == 1
    assert df_1h["open"].iloc[0] == 10000.0
    assert df_1h["high"].iloc[0] == 10100.0
    assert df_1h["low"].iloc[0] == 10000.0
    assert df_1h["close"].iloc[0] == 10100.0
    assert df_1h["volume"].iloc[0] == 12.0
    assert df_1h["trade_count"].iloc[0] == 12


def test_tardis_aggregate_4h_causal_contract():
    # 7 hourly bars (one complete 4h bucket, one incomplete 3-bar bucket)
    base_dt = pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
    bars_1h = []
    for i in range(7):
        ts = base_dt + pd.Timedelta(hours=i)
        bars_1h.append({
            "timestamp": ts.isoformat(),
            "open": 40000 + i * 10,
            "high": 40050 + i * 10,
            "low": 39980 + i * 10,
            "close": 40020 + i * 10,
            "volume": 100.0,
            "trade_count": 50
        })
    df_1h = pd.DataFrame(bars_1h)

    df_4h, meta = TardisSampleParser.aggregate_4h_from_1h(df_1h)

    # Only bucket 00:00 (containing hours 0, 1, 2, 3) is complete.
    # Bucket 04:00 (containing only hours 4, 5, 6) must be dropped as incomplete.
    assert len(df_4h) == 1
    assert meta["completed_4h_candles"] == 1
    assert meta["incomplete_dropped_buckets"] == 1
    assert df_4h["constituent_1h_bars"].iloc[0] == 4
    assert df_4h["open"].iloc[0] == 40000.0
    assert df_4h["close"].iloc[0] == 40020 + 3 * 10

