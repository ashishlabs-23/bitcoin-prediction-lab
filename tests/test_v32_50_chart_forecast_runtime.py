from engine.forecast_engine_15m import _classify_candle_freshness


def test_forecast_freshness_uses_source_candle_granularity_not_forecast_horizon():
    candle_open = 1_793_032_200
    now = candle_open + 900 + 16 * 60

    candle_close, seconds_since_close, status = _classify_candle_freshness(
        now_epoch=now,
        candle_open_epoch=candle_open,
        data_granularity_sec=900
    )

    assert candle_close == candle_open + 900
    assert seconds_since_close == 16 * 60
    assert status == "DELAYED"


def test_forecast_freshness_boundaries_are_source_interval_relative():
    candle_open = 1_793_032_200
    candle_granularity = 900

    assert _classify_candle_freshness(
        candle_open + candle_granularity * 2,
        candle_open,
        candle_granularity
    )[2] == "FRESH"
    assert _classify_candle_freshness(
        candle_open + candle_granularity * 3,
        candle_open,
        candle_granularity
    )[2] == "DELAYED"
    assert _classify_candle_freshness(
        candle_open + candle_granularity * 4 + 1,
        candle_open,
        candle_granularity
    )[2] == "STALE"
