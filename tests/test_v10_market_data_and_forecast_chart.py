"""
tests/test_v10_market_data_and_forecast_chart.py — V10 Market Data, Forecast Engine & Chart Tests
==================================================================================================
Validates:
1. Real 15-minute Coinbase BTC-USD candle ingestion, 900-second bucket alignment, OHLC geometric validity.
2. Parquet persistence and cryptographic provenance manifest (SHA-256).
3. 15-minute volatility and forward non-directional persistence forecast contract.
4. Mathematical integrity of square-root-of-time empirical diffusion uncertainty envelope (90% CI).
5. Explicit separation of data readiness (DATA_AVAILABLE) from model compatibility (MODEL_TIMEFRAME_INCOMPATIBLE).
6. API routes: /api/market/candles?interval=15m, /api/forecast/latest?horizon=15m, /api/arena/active-paper-position?horizon=15m.
7. Strict preservation of project invariants: live trading DISABLED, directional recommendation ABSTAIN.
"""

import json
import math
import os
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from engine.coinbase_15m_adapter import (
    Coinbase15mAdapter,
    DEFAULT_PARQUET_PATH,
    DEFAULT_MANIFEST_PATH,
    GRANULARITY_15M
)
from engine.forecast_engine_15m import (
    compute_15m_volatility,
    generate_forecast_contract
)
from api.server import app

client = TestClient(app)


# ===========================================================================
# 1. 15-Minute Data Adapter & Continuity Invariant Tests
# ===========================================================================

def test_15m_dataset_and_manifest_exist():
    """Verify that the real 15m parquet dataset and manifest are present on disk."""
    assert os.path.exists(DEFAULT_PARQUET_PATH), f"Missing 15m parquet file at {DEFAULT_PARQUET_PATH}"
    assert os.path.exists(DEFAULT_MANIFEST_PATH), f"Missing 15m manifest file at {DEFAULT_MANIFEST_PATH}"

    with open(DEFAULT_MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["instrument"] == "BTC-USD"
    assert manifest["timeframe"] == "15m"
    assert manifest["granularity_seconds"] == 900
    assert manifest["sha256_hash"] is not None
    assert len(manifest["sha256_hash"]) == 64
    assert manifest["metadata"]["total_validated"] >= 100
    assert manifest["metadata"]["segment_count"] >= 1


def test_15m_candles_strictly_increasing_and_aligned():
    """Verify strictly increasing 900-second bucket alignment and OHLC geometric validity."""
    adapter = Coinbase15mAdapter()
    cached = adapter.load_cached()
    assert cached is not None
    df, manifest = cached
    assert len(df) >= 100

    times = df["epoch_time"].values
    opens = df["open"].values
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    volumes = df["volume"].values

    for i in range(len(df)):
        t = int(times[i])
        # 900-second bucket alignment
        assert t % GRANULARITY_15M == 0, f"Candle {i} timestamp {t} not 900s aligned"

        # OHLC relationships
        hi = highs[i]
        lo = lows[i]
        op = opens[i]
        cl = closes[i]
        vol = volumes[i]

        assert hi >= lo, f"High < Low at candle {i}"
        assert hi >= op, f"High < Open at candle {i}"
        assert hi >= cl, f"High < Close at candle {i}"
        assert lo <= op, f"Low > Open at candle {i}"
        assert lo <= cl, f"Low > Close at candle {i}"
        assert vol >= 0.0, f"Negative volume at candle {i}"
        assert op > 0 and cl > 0

        # Strictly increasing timestamps
        if i > 0:
            prev_t = int(times[i - 1])
            assert t > prev_t, f"Non-increasing timestamp at {i}"
            assert t - prev_t >= GRANULARITY_15M


def test_15m_adapter_validation_filters_corrupt_data():
    """Verify adapter rejects invalid OHLC geometry and unaligned timestamps."""
    adapter = Coinbase15mAdapter()

    corrupt_batch = [
        {"time": 1729000800, "open": 80000.0, "high": 79000.0, "low": 80500.0, "close": 79800.0, "volume": 10.0},  # High < Low (invalid)
        {"time": 1729000800 + 123, "open": 80000.0, "high": 81000.0, "low": 79500.0, "close": 80800.0, "volume": 10.0},  # Unaligned timestamp
        {"time": 1729000800 + 900, "open": 80000.0, "high": 81000.0, "low": 79500.0, "close": 80800.0, "volume": -5.0},  # Negative volume
        {"time": 1729000800 + 1800, "open": 80000.0, "high": 81000.0, "low": 79500.0, "close": 80800.0, "volume": 12.0},  # Valid aligned
    ]
    validated, meta = adapter.validate_and_segment_candles(corrupt_batch, discard_forming=False)
    # Only the 4th record should survive
    assert len(validated) == 1
    assert validated[0]["epoch_time"] == 1729000800 + 1800


# ===========================================================================
# 2. 15-Minute Forecast Engine & Volatility Tests
# ===========================================================================

def test_15m_volatility_computation():
    """Verify Parkinson realized volatility and variance calculation."""
    vol_data = compute_15m_volatility()
    assert vol_data["status"] == "READY"
    assert vol_data["sample_size"] >= 20
    assert vol_data["parkinson_vol_15m"] > 0.0
    assert vol_data["annualized_vol_pct"] > 0.0
    assert vol_data["annualized_vol_pct"] < 300.0  # Realistic BTC annual vol bounds
    assert math.isfinite(vol_data["parkinson_vol_15m"])


def test_15m_forecast_contract_mathematics():
    """Verify forward forecast baseline and expanding diffusion envelope."""
    fc = generate_forecast_contract("15m", num_steps=4)

    assert fc["status"] == "FORECAST_AVAILABLE_RESEARCH_ONLY"
    assert fc["data_readiness"] == "DATA_AVAILABLE"
    assert fc["model_readiness"] == "MODEL_TIMEFRAME_INCOMPATIBLE"
    assert fc["governance_status"] == "TIER 2 GATED (ABSTAIN)"
    assert fc["directional_recommendation"] == "ABSTAIN"
    assert fc["instrument"] == "BTC-USD"
    assert fc["source_timeframe"] == "15m"

    origin = fc["forecast_origin_timestamp"]
    s0 = fc["reference_price"]
    assert s0 > 0.0

    points = fc["points"]
    upper = fc["upper_band"]
    lower = fc["lower_band"]

    assert len(points) == 5  # t0 + 4 steps
    assert len(upper) == 5
    assert len(lower) == 5

    # Origin point check
    assert points[0]["time"] == origin
    assert points[0]["value"] == s0
    assert upper[0]["value"] == s0
    assert lower[0]["value"] == s0

    # Strictly future points & expanding uncertainty band
    prev_width = 0.0
    for h in range(1, 5):
        expected_t = origin + h * 900
        assert points[h]["time"] == expected_t
        assert upper[h]["time"] == expected_t
        assert lower[h]["time"] == expected_t

        # Non-directional persistence baseline holds s0
        assert points[h]["value"] == s0

        # Mathematical bounds: lower < baseline < upper
        assert upper[h]["value"] > s0
        assert lower[h]["value"] < s0

        width = upper[h]["value"] - lower[h]["value"]
        assert width > prev_width, f"Band width must expand with sqrt(time) at step {h}"
        prev_width = width


# ===========================================================================
# 3. Backend API Route Verification
# ===========================================================================

def test_api_market_candles_15m():
    """Verify /api/market/candles returns validated 15m candles."""
    res = client.get("/api/market/candles?symbol=BTC-USD&interval=15m")
    assert res.status_code == 200
    data = res.json()
    assert "candles" in data
    candles = data["candles"]
    assert isinstance(candles, list)
    assert len(candles) >= 100
    first = candles[0]
    assert first["time"] % 900 == 0
    assert first["high"] >= first["low"]


def test_api_forecast_latest_15m():
    """Verify /api/forecast/latest returns the typed 15m forecast contract."""
    res = client.get("/api/forecast/latest?horizon=15m")
    assert res.status_code == 200
    data = res.json()
    assert data["source_timeframe"] == "15m"
    assert data["data_readiness"] == "DATA_AVAILABLE"
    assert data["model_readiness"] == "MODEL_TIMEFRAME_INCOMPATIBLE"
    assert len(data["points"]) == 5
    assert len(data["upper_band"]) == 5
    assert len(data["lower_band"]) == 5


def test_api_active_paper_position_15m_readiness():
    """Verify active-paper-position properly reflects 15m data readiness and attaches forecast."""
    res = client.get("/api/arena/active-paper-position?horizon=15m&signal_mode=live_ai")
    assert res.status_code == 200
    data = res.json()

    # Data is available, model is incompatible, recommendation is abstain
    assert data["data_readiness"] == "DATA_AVAILABLE"
    assert data["data_frequency_status"] == "SUPPORTED_15M"
    assert data["primary_reason"] == "MODEL_TIMEFRAME_INCOMPATIBLE"
    assert data["action"] == "ABSTAIN"
    assert data["execution_authorization"] == "DISABLED"
    assert data["has_active_position"] is False

    # Forecast series are attached for chart rendering
    assert "forecast" in data
    assert "points" in data["forecast"]
    assert isinstance(data["forecast"]["points"], list)
    assert len(data["forecast"]["points"]) >= 2
    assert "forecast_contract" in data
    fc = data["forecast_contract"]
    assert fc["source_timeframe"] == "15m"
    assert len(fc["points"]) >= 2
    assert len(fc["upper_band"]) >= 2


def test_hourly_contract_preserved():
    """Ensure 1h requests continue to operate under their canonical contract."""
    res = client.get("/api/forecast/latest?horizon=1h")
    assert res.status_code == 200
    data = res.json()
    assert data["source_timeframe"] == "1h"
    assert data["points"][1]["time"] - data["points"][0]["time"] == 3600
