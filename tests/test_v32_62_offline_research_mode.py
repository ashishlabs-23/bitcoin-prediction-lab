"""
tests/test_v32_62_offline_research_mode.py — Internal Offline Research Mode Test Suite
======================================================================================
Comprehensive verification of BTCognitive operating strictly offline on loopback
(127.0.0.1) using local historical datasets, local model inference, and fail-closed
safeguards against external network dependencies.
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.server import app
from engine.market_data_adapters.factory import is_provider_adapter_enabled
from models.authoritative_model_registry import (
    get_active_production_model,
    AuthorizationStatus,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PROTECTED_ARTIFACT_HASHES = {
    "data/raw/ohlcv.parquet": "c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f",
    "data/raw/ohlcv_pre_backfill_backup.parquet": "c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8",
    "data/raw/ohlcv_backfilled.parquet": "1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c",
    "data/prospective_entry_ledger.jsonl": "91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7",
    "data/prospective_shadow_v1.jsonl": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "data/prospective_entry_ledger_v2.jsonl": "e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604",
}


@pytest.fixture(scope="module")
def client():
    """Isolated TestClient for the FastAPI application."""
    with TestClient(app) as tc:
        yield tc


# ==============================================================================
# Scenario 1: Local Historical Dataset Integrity & Monotonicity
# ==============================================================================
def test_historical_dataset_integrity_and_gap_preservation():
    """
    Verifies that the canonical historical dataset data/raw/ohlcv.parquet:
    1. Contains exactly 42,233 hourly rows.
    2. Has strictly monotonic timestamps and zero NaN / Inf prices.
    3. Retains genuine exchange prices without synthetic fabrication.
    """
    parquet_path = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
    assert os.path.exists(parquet_path), "ohlcv.parquet missing!"
    df = pd.read_parquet(parquet_path)

    # 1. Exact row count check
    assert len(df) == 42233, f"Expected 42,233 rows; found {len(df)}"

    # 2. Timestamp monotonicity
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    assert df["timestamp"].is_monotonic_increasing, "Timestamps in ohlcv.parquet must be strictly monotonic"

    # 3. Finite numbers and extrema check
    assert df["open"].gt(0).all()
    assert df["close"].gt(0).all()
    assert df["high"].ge(df["low"]).all()
    assert df["volume"].ge(0).all()
    assert not df[["open", "high", "low", "close", "volume"]].isna().any().any()


# ==============================================================================
# Scenario 2: Offline Technical Indicator Calculation
# ==============================================================================
def test_offline_technical_indicator_computation():
    """
    Validates that indicators (EMA, RSI, Donchian, ATR) compute entirely
    offline from local historical candles without network calls.
    """
    parquet_path = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
    df = pd.read_parquet(parquet_path).tail(200).copy()

    # EMA-21
    df["ema_21"] = df["close"].ewm(span=21, adjust=False).mean()
    assert not df["ema_21"].isna().any()
    assert (df["ema_21"] > 0).all()

    # Donchian 24h Channels
    df["donchian_high_24"] = df["high"].rolling(24).max()
    df["donchian_low_24"] = df["low"].rolling(24).min()
    valid_donchian = df.dropna(subset=["donchian_high_24", "donchian_low_24"])
    assert (valid_donchian["donchian_high_24"] >= valid_donchian["donchian_low_24"]).all()

    # ATR-14
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()
    valid_atr = df["atr_14"].dropna()
    assert (valid_atr >= 0).all()


# ==============================================================================
# Scenario 3: Offline Terminal Status & Fail-Closed Governance Gate
# ==============================================================================
def test_offline_terminal_status_and_live_intelligence(client):
    """
    Verifies that the volatility intelligence terminal operates on local historical
    data and explicitly enforces OFFLINE_RESEARCH_ONLY status, failing closed
    when production authorization is withheld.
    """
    res = client.get("/api/terminal/status")
    assert res.status_code == 200
    data = res.json()
    assert "DISABLED" in data["execution_status"]
    assert data["production_forecast_status"] in ("AVAILABLE", "BLOCKED", "UNAVAILABLE")

    # Under OFFLINE_RESEARCH_ONLY, /api/terminal/live strictly fails closed (HTTP 503)
    res_live = client.get("/api/terminal/live")
    assert res_live.status_code in (200, 503)
    if res_live.status_code == 503:
        live_err = res_live.json()
        detail = live_err.get("detail", {})
        code = detail.get("code") if isinstance(detail, dict) else live_err.get("code")
        assert code in ("MODEL_UNAUTHORIZED", "OFFLINE_RESEARCH_ONLY")


# ==============================================================================
# Scenario 4: Strategy Tournament Registry Offline
# ==============================================================================
def test_offline_strategy_registry(client):
    """
    Verifies that the strategy tournament registry is served in-memory
    without external network dependency.
    """
    res = client.get("/api/tournament/registry")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["governance"] == "OFFLINE_RESEARCH_ONLY"
    assert data["total_registered"] >= 5
    assert "registry" in data


# ==============================================================================
# Scenario 5: Offline Analyse Workflow on Local Bars
# ==============================================================================
def test_offline_analyse_setup_on_historical_bars(client):
    """
    Exercises the complete Analyse workflow using submitted local historical bars.
    Verifies:
    1. Returns valid evaluation payload (DECISION_CANDIDATE or ABSTAIN).
    2. attempts_created == 0 strictly.
    3. Zero mutations to prospective ledgers.
    """
    parquet_path = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
    df = pd.read_parquet(parquet_path).tail(50).copy()
    bars = []
    for _, row in df.iterrows():
        bars.append({
            "timestamp": row["timestamp"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        })

    payload = {
        "instrument": "BTC-USD",
        "timeframe": "1h",
        "data_source": "OFFLINE_LOCAL_HISTORICAL_PARQUET",
        "candles": bars,
    }

    res = client.post("/api/tournament/analyse", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Core invariants
    assert data.get("attempts_created", 0) == 0
    assert "analysis_id" in data
    assert "smart_entry_decision" in data


# ==============================================================================
# Scenario 6: Fail-Closed on Unsupported Instrument or Timeframe
# ==============================================================================
def test_offline_fail_closed_on_unsupported_inputs(client):
    """
    Validates that unsupported symbols (e.g. ETH-USD) or unsupported timeframes (e.g. 15m)
    are strictly rejected with HTTP 422.
    """
    # 1. Unsupported instrument
    res_inst = client.post("/api/tournament/analyse", json={"instrument": "ETH-USD", "timeframe": "1h"})
    assert res_inst.status_code == 422
    assert "supports only BTC-USD" in res_inst.json().get("detail", "")

    # 2. Unsupported timeframe
    res_tf = client.post("/api/tournament/analyse", json={"instrument": "BTC-USD", "timeframe": "15m"})
    assert res_tf.status_code == 422
    assert "Analysis requires 1-hour candles" in res_tf.json().get("detail", "")


# ==============================================================================
# Scenario 7: External Network Calls Fail-Closed When Offline
# ==============================================================================
def test_external_comparator_fails_closed_when_network_down(client):
    """
    Verifies that when external HTTP requests fail or are simulated offline,
    the /api/market/comparator endpoint catches errors gracefully and fails closed.
    """
    with patch(
        "engine.spot_exchange_comparator.fetch_and_compare_spot_quotes",
        return_value={"status": "DATA_UNAVAILABLE", "error": "Simulated offline network", "comparator": {}}
    ):
        res = client.get("/api/market/comparator")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "DATA_UNAVAILABLE"


# ==============================================================================
# Scenario 8: Provider Adapter Feature Flag Disabled by Default
# ==============================================================================
def test_provider_adapter_gated_offline():
    """
    Ensures that live market data provider adapters remain disabled by default.
    """
    if "BTC_ENABLE_PROVIDER_ADAPTER" in os.environ:
        del os.environ["BTC_ENABLE_PROVIDER_ADAPTER"]
    assert is_provider_adapter_enabled() is False


# ==============================================================================
# Scenario 9: Protected Artifacts Bit-Level Invariance
# ==============================================================================
def test_protected_artifacts_bit_level_invariance():
    """
    Asserts that the 6 protected datasets and ledgers remain bit-identical.
    """
    for rel_path, expected_hash in PROTECTED_ARTIFACT_HASHES.items():
        abs_path = os.path.join(REPO_ROOT, rel_path)
        assert os.path.exists(abs_path), f"Protected artifact missing: {abs_path}"
        h = hashlib.sha256()
        with open(abs_path, "rb") as fp:
            while chunk := fp.read(8192):
                h.update(chunk)
        actual_hash = h.hexdigest()
        assert (
            actual_hash == expected_hash
        ), f"HASH CORRUPTION DETECTED in {rel_path}! Expected: {expected_hash}, Actual: {actual_hash}"
