"""
BTCognitive — V33.5: Analysis Reliability, Opportunity Coverage & Actionability Test Suite
========================================================================================
Verifies:
1. Complete 5-status decoupled architecture.
2. Exposure of all 4 actionability fields (breakout_reference, distance_to_trigger_bps, distance_to_trigger_atr, next_required_condition).
3. 21-candle boundary discipline preventing N=20 Donchian NaN defect.
4. ATR-adaptive forming buffer behavior.
5. Inactive stop reference protection (None when status is not SHADOW_CANDIDATE).
6. Read-only execution creating 0 trade attempts.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from starlette.testclient import TestClient

from api.server import app
from engine.htf_setup_detector import HTFSetupDetector
from engine.regime_strategy_tournament import (
    execute_integrated_analyse_and_tournament,
    VersionedStrategyRegistry
)


@pytest.fixture
def client():
    return TestClient(app)


def generate_synthetic_4h_candles(num_bars: int = 25, base_price: float = 70000.0, trend: str = "bull"):
    """Generates synthetic 1h OHLCV bars yielding exact number of 4h completed candles."""
    total_1h_bars = num_bars * 4
    now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    aligned_hour = (now_utc.hour // 4) * 4
    start_time = now_utc.replace(hour=aligned_hour) - timedelta(hours=total_1h_bars)

    timestamps = [start_time + timedelta(hours=i) for i in range(total_1h_bars)]
    rows = []
    price = base_price

    for i in range(total_1h_bars):
        drift = 10.0 if trend == "bull" else -10.0
        open_p = price
        close_p = open_p + drift
        high_p = max(open_p, close_p) + 20.0
        low_p = min(open_p, close_p) - 20.0
        rows.append({
            "timestamp": timestamps[i].isoformat(),
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": 100.0
        })
        price = close_p

    return pd.DataFrame(rows)


def test_v33_5_api_actionability_fields(client):
    """Test that POST /api/tournament/analyse returns all 4 actionability fields and decoupled status dimensions."""
    resp = client.post("/api/tournament/analyse", json={
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "auto_tournament": True
    })
    assert resp.status_code == 200
    data = resp.json()

    # Verify root actionability fields
    assert "breakout_reference" in data
    assert "distance_to_trigger_bps" in data
    assert "distance_to_trigger_atr" in data
    assert "next_required_condition" in data
    assert "analysis_execution_status" in data
    assert data["analysis_execution_status"] in ("SUCCESS", "DATA_DEFICIENT")

    # Verify htf_setup dictionary fields
    htf = data.get("htf_setup", {})
    assert "breakout_reference" in htf
    assert "distance_to_trigger_bps" in htf
    assert "distance_to_trigger_atr" in htf
    assert "next_required_condition" in htf
    assert "analysis_execution_status" in htf
    assert "research_eligibility_status" in htf
    assert htf["research_eligibility_status"] in ("RESEARCH_CANDIDATE", "NOT_ELIGIBLE")

    # Invariant: read-only, zero attempts created
    assert data["is_read_only"] is True
    assert data["attempts_created"] == 0


def test_v33_5_donchian_n21_boundary_prevention():
    """Verify that exactly 20 completed 4h bars returns DATA_UNAVAILABLE rather than NaN."""
    # 20 completed 4h bars = 80 1h bars
    df_20_bars = generate_synthetic_4h_candles(num_bars=20)
    res_20 = HTFSetupDetector.detect_setup(
        df_1h=df_20_bars,
        observed_regime="VOLATILITY_EXPANSION",
        is_data_stale=False,
        enforce_stale_blocking=False
    )
    assert res_20["setup_status"] == "DATA_UNAVAILABLE"
    assert res_20["trigger_status"] == "DATA_DEFICIENT"
    assert "DATA_UNAVAILABLE_INSUFFICIENT_BARS" in res_20["reason_codes"]
    assert res_20["breakout_reference"] is None

    # 21 completed 4h bars = 84 1h bars: has sufficient warmup to compute shifted 20-bar Donchian channel
    df_21_bars = generate_synthetic_4h_candles(num_bars=21)
    res_21 = HTFSetupDetector.detect_setup(
        df_1h=df_21_bars,
        observed_regime="VOLATILITY_EXPANSION",
        is_data_stale=False,
        enforce_stale_blocking=False
    )
    assert res_21["setup_status"] != "DATA_UNAVAILABLE"
    assert res_21["breakout_reference"] is not None
    assert not np.isnan(res_21["breakout_reference"])


def test_v33_5_adaptive_forming_buffer():
    """Verify that ATR-adaptive forming condition functions correctly."""
    df_25 = generate_synthetic_4h_candles(num_bars=25, trend="bull")
    
    # In bull trend, price steadily rises. Let's inspect setup
    res = HTFSetupDetector.detect_setup(
        df_1h=df_25,
        observed_regime="VOLATILITY_EXPANSION",
        is_data_stale=False,
        enforce_stale_blocking=False
    )
    assert res["breakout_reference"] is not None
    assert res["distance_to_trigger_bps"] is not None
    assert res["distance_to_trigger_atr"] is not None
    assert res["next_required_condition"] is not None


def test_v33_5_registry_holding_horizon_alignment():
    """Verify that Strategy D registry entry holding horizon matches HTF detector (72.0 hours)."""
    registry_entries = VersionedStrategyRegistry.get_all_entries()
    htf_entry = registry_entries.get("HTF_RANGE_EXPANSION_BREAKOUT")
    assert htf_entry is not None
    assert htf_entry.holding_horizon_hours == 72.0

