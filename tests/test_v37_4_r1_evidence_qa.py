from datetime import datetime, timezone

from api import market_monitor_routes


def test_active_bitstamp_snapshot_with_future_clock_skew_is_not_fresh(monkeypatch):
    now_epoch = 1_700_000_000.0
    future_timestamp = datetime.fromtimestamp(
        now_epoch + 6, timezone.utc
    ).isoformat().replace("+00:00", "Z")
    monkeypatch.setattr(market_monitor_routes.time, "time", lambda: now_epoch)

    snapshot = {
        "status": "ACTIVE",
        "feed_state": "CONNECTED",
        "symbol": "BTC/USD",
        "exchange": "Bitstamp",
        "market_type": "SPOT",
        "interval": "1m",
        "source": "bitstamp",
        "last_event_timestamp": future_timestamp,
        "last_receive_timestamp": future_timestamp,
        "event_to_receive_delay_seconds": 0.0,
        "candles": [{
            "time": int(now_epoch) - 60,
            "open": 68_000.0,
            "high": 68_100.0,
            "low": 67_900.0,
            "close": 68_050.0,
            "volume": 1.0,
            "is_closed": True,
            "quality_status": "VALID",
            "source": "bitstamp",
        }],
    }

    normalized = market_monitor_routes._normalize_bitstamp_snapshot(snapshot, 10)

    assert normalized["status"] == "STALE"
    assert normalized["freshness_status"] == "STALE"
    assert normalized["analysis"]["engine_invoked"] is False
