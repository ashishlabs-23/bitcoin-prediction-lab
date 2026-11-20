import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app

client = TestClient(app)


def _valid_snapshot():
    now_utc = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    closes = [62000.0 + i * 80 for i in range(40)]
    candles = []
    for i, close in enumerate(closes):
        candle_ts = (now_utc - __import__("datetime").timedelta(hours=39 - i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        candles.append({
            "timestamp_utc": candle_ts,
            "open": close - 40.0,
            "high": close + 120.0,
            "low": close - 140.0,
            "close": close,
        })
    return {
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "timestamp_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "live_price": 65000.0,
        "candles": candles,
        "market_snapshot": {
            "ofi": 0.85,
            "hawkes": 2.5,
            "vpin": 0.18,
            "spread_bps": 2.0,
            "depth_score": 0.82,
            "is_expansion": True,
        },
        "enabled_indicators": ["ofi", "hawkes", "vpin", "rv_5m", "liquidations"],
        "regime": "VOL_EXPANDING",
        "c2_health": "UNAVAILABLE",
        "user_direction_preference": "AUTO",
    }


def test_smart_entry_endpoint_accepts_valid_snapshot():
    response = client.post("/api/research/smart-entry", json=_valid_snapshot())
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["status"] in {"SUCCESS", "ABSTAIN"}
    assert data["instrument"] == "BTC-USD"
    assert data["timeframe"] == "1h"
    assert data["decision_action"] in {"ACCEPTED_RESEARCH_CANDIDATE", "ABSTAIN"}

    if data["status"] == "SUCCESS":
        assert data["direction"] in {"LONG", "SHORT"}
        assert data["candidate"] is not None
        assert data["resolution"] is not None


def test_smart_entry_endpoint_rejects_invalid_instrument_or_stale_data():
    payload = _valid_snapshot()
    payload["instrument"] = "BTCUSDT"
    response = client.post("/api/research/smart-entry", json=payload)
    assert response.status_code in {400, 422}

    stale_payload = _valid_snapshot()
    stale_payload["timestamp_utc"] = "2020-01-01T00:00:00Z"
    response = client.post("/api/research/smart-entry", json=stale_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ABSTAIN"
    assert data["decision_action"] == "ABSTAIN"
    assert data["data_quality_status"] == "STALE"
    assert data["timeframe"] == stale_payload["timeframe"]


def test_smart_entry_endpoint_rejects_inconsistent_candle_cadence():
    payload = _valid_snapshot()
    start_dt = __import__("datetime").datetime.strptime(payload["candles"][0]["timestamp_utc"], "%Y-%m-%dT%H:%M:%SZ")
    payload["candles"] = [
        {
            "timestamp_utc": payload["candles"][0]["timestamp_utc"],
            "open": 62000.0,
            "high": 62050.0,
            "low": 61950.0,
            "close": 62020.0,
        }
    ] + [
        {
            "timestamp_utc": (start_dt + __import__("datetime").timedelta(minutes=1) * (idx + 1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "open": 62000.0 + idx * 10,
            "high": 62050.0 + idx * 10,
            "low": 61950.0 + idx * 10,
            "close": 62020.0 + idx * 10,
        }
        for idx in range(1, 6)
    ]
    response = client.post("/api/research/smart-entry", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ABSTAIN"
    assert data["decision_action"] == "ABSTAIN"
    assert data["data_quality_status"] == "INVALID_TIMEFRAME_CADENCE"


def test_smart_entry_endpoint_rejects_missing_fields_with_422():
    response = client.post("/api/research/smart-entry", json={"instrument": "BTC-USD"})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    # Confirm detail lists missing fields
    missing_locs = [item.get("loc", [])[-1] for item in data["detail"] if item.get("type") == "missing"]
    assert "timestamp_utc" in missing_locs


def test_smart_entry_endpoint_rejects_unsupported_timeframe():
    payload = _valid_snapshot()
    payload["timeframe"] = "2h"
    response = client.post("/api/research/smart-entry", json=payload)
    assert response.status_code == 400
    assert "Unsupported timeframe" in response.text


def test_smart_entry_endpoint_abstains_on_non_positive_candle():
    payload = _valid_snapshot()
    payload["candles"][0]["close"] = -100.0
    response = client.post("/api/research/smart-entry", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ABSTAIN"
    assert data["candidate"] is None
    assert data["data_quality_status"] == "INSUFFICIENT_EVIDENCE"


def test_smart_entry_endpoint_live_terminal_telemetry_flow():
    """Verifies that a Live Terminal BTCUSD telemetry payload with active AI prediction conditioning is accepted."""
    payload = _valid_snapshot()
    # Emulate real Live Terminal Coinbase Spot telemetry
    payload["instrument"] = "BTC-USD"
    payload["live_price"] = 65420.50
    payload["regime"] = "VOL_EXPANDING"
    payload["c2_health"] = "UNAVAILABLE"
    payload["user_direction_preference"] = "LONG"
    payload["cost_scenario"] = "COINBASE_RETAIL_87BPS"
    payload["market_snapshot"]["realized_vol_24h_ann"] = 0.485
    payload["market_snapshot"]["bid_ask_spread_bps"] = 1.2

    response = client.post("/api/research/smart-entry", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify all 10 required items from section 2 are present or resolvable
    # 1. Market regime & volatility state
    assert data["market_regime"] == "VOL_EXPANDING"
    # 2. Selected strategy & rationale
    assert "selected_strategy_id" in data
    # 3. Candidate direction
    assert data["direction"] in {"LONG", "SHORT", "NEUTRAL"}
    # 4 & 5. Proposed entry, TP, SL (if candidate accepted)
    if data["candidate"]:
        cand = data["candidate"]
        assert cand["entry_reference_price"] > 0
        assert cand["take_profit_price"] > 0
        assert cand["stop_loss_price"] > 0
        # 6. RRR & transaction costs
        assert cand["k_tp"] / cand["k_sl"] == 1.5
        assert cand["round_trip_friction_bps"] == 87.0
        # 7. Horizon
        assert cand["horizon_bars"] == 24
    # 8. Evidence quality
    assert data["data_quality_status"] in {"VALID", "INSUFFICIENT_EVIDENCE"}
    # 9. Reasons
    assert isinstance(data["reasons"], list)
    # 10. Data source & freshness
    assert data["instrument"] == "BTC-USD"
    assert data["execution_authorization"] == "DISABLED — ANALYSIS ONLY"
    assert data["governance_status"] == "OFFLINE_RESEARCH_ONLY"


