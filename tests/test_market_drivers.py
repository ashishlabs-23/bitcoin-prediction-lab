import math
import time

from api.market_drivers import (
    _derive_technical,
    _normalise_candles,
    build_empirical_forecast,
)


def _candles(n=24 * 100):
    # Deterministic bounded price sequence; timestamps end at the last closed hour.
    end = int(time.time() // 3600) * 3600 - 3600
    rows = []
    price = 60_000.0
    for i in range(n):
        # Fixed, non-random alternating return sequence with a small upward drift.
        delta = (0.0012 if i % 3 else -0.0009) + (0.00015 if i % 11 == 0 else 0)
        new_price = price * math.exp(delta)
        rows.append({
            "time": float(end - (n - 1 - i) * 3600),
            "open": price,
            "high": max(price, new_price) * 1.0005,
            "low": min(price, new_price) * 0.9995,
            "close": new_price,
            "volume": 100.0 + (i % 13),
        })
        price = new_price
    return rows


def test_forecast_has_non_overlapping_ranges_and_no_trade_authorization():
    candles = _candles()
    result = build_empirical_forecast(candles, candles[-1]["close"], "24h")
    assert result["availability"] == "AVAILABLE"
    assert result["status"] == "EXPERIMENTAL_BASELINE"
    assert result["live_capital_authorized"] is False
    assert result["probability_pct"] is None
    q = result["price_quantiles_usd"]
    assert 0 < q["p10"] <= q["p50"] <= q["p90"]
    assert result["sample_blocks"] >= 20
    assert result["tp"] is None and result["sl"] is None


def test_forecast_is_unavailable_when_history_is_too_short():
    result = build_empirical_forecast(_candles(24 * 5), 60_000.0, "24h")
    assert result["availability"] == "UNAVAILABLE"
    assert result["reason"] == "INSUFFICIENT_NON_OVERLAPPING_HISTORY"
    assert result["price_quantiles_usd"] is None


def test_invalid_price_never_produces_a_fabricated_forecast():
    result = build_empirical_forecast(_candles(), None, "24h")
    assert result["availability"] == "UNAVAILABLE"
    assert result["reason"] == "NO_VALID_SPOT_PRICE"
    assert result.get("price_quantiles_usd") is None


def test_candle_validation_discards_incomplete_and_malformed_rows():
    end = int(time.time() // 3600) * 3600
    rows = [
        {"time": end - 7200, "open": 100, "high": 102, "low": 99, "close": 101, "volume": 2},
        {"time": end - 3600, "open": 101, "high": 103, "low": 100, "close": 102, "volume": 2},
        {"time": end, "open": 102, "high": 104, "low": 101, "close": 103, "volume": 2},
        {"time": end - 10800, "open": 100, "high": 101, "low": 102, "close": 100, "volume": 2},
    ]
    valid = _normalise_candles(rows, now=end + 10)
    assert [int(row["time"]) for row in valid] == [end - 7200, end - 3600]


def test_technical_indicators_are_data_derived():
    candles = _candles()
    result = _derive_technical(candles)
    assert result["momentum_24h_pct"] is not None
    assert result["realized_volatility_24h_pct"] >= 0
    assert 0 <= result["rsi_14"] <= 100
    assert result["volume_ratio_24h"] is not None