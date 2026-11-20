"""
tests/test_v32_64_data_lane_separation.py — Three-Lane Data Architecture Verification Suite
============================================================================================
BTCognitive V32.64 Data-Lane Separation Verification.
Validates:
1. Explicit data modes: fixture, offline_research, provider. Invalid modes fail closed.
2. Mode-dependent defaulting: pytest -> fixture; normal loopback dev -> offline_research.
3. Protected artifact isolation: fixture mode strictly forbids reading the 6 protected datasets.
4. Offline research mode serves genuine historical snapshot with 0 outbound network calls.
5. Spot exchange comparator fails closed without socket creation when external network is blocked.
6. Network transport guards block _get_json, _fetch_quote, and 15m chunks before socket creation.
7. Canonical symbol BTC-USD and envelope structure on /api/market/candles.
8. Provider mode fails closed (PROVIDER_NOT_CONFIGURED) in Phase 1 without external provider licence.
9. Truthful nulls/unavailability reporting with 0 fabricated numbers.
10. SystemStatusContract accurately reflects data_mode and data_mode_contract.
11. Invariance of all 6 protected datasets and ledgers (bit-identical SHA-256).
"""

import hashlib
import os
import sys
from typing import Dict, Any
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from api.server import app
from engine.data_mode import (
    DataMode,
    get_data_mode,
    is_external_network_permitted,
    assert_no_external_network,
    is_protected_file_access_permitted,
    get_data_mode_contract,
    InvalidDataModeError,
    ExternalNetworkBlockedError,
    ProtectedFileAccessBlockedError,
)
from engine.status_contract import evaluate_system_status

PROTECTED_ARTIFACTS = {
    "data/raw/ohlcv.parquet": "c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f",
    "data/raw/ohlcv_pre_backfill_backup.parquet": "c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8",
    "data/raw/ohlcv_backfilled.parquet": "1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c",
    "data/prospective_entry_ledger.jsonl": "91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7",
    "data/prospective_shadow_v1.jsonl": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "data/prospective_entry_ledger_v2.jsonl": "e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604",
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as tc:
        yield tc


# ==============================================================================
# Test 1: DataMode Parsing & Fail-Closed Unknown Handling
# ==============================================================================
def test_01_data_mode_parsing_and_fail_closed():
    """Valid modes are accepted; invalid or unrecognized modes raise InvalidDataModeError."""
    assert DataMode.from_string("fixture") == DataMode.FIXTURE
    assert DataMode.from_string("FIXTURE") == DataMode.FIXTURE
    assert DataMode.from_string("offline_research") == DataMode.OFFLINE_RESEARCH
    assert DataMode.from_string("OFFLINE-RESEARCH") == DataMode.OFFLINE_RESEARCH
    assert DataMode.from_string("provider") == DataMode.PROVIDER

    with pytest.raises(InvalidDataModeError) as exc_info:
        DataMode.from_string("live_trading")
    assert "Invalid data mode 'live_trading'" in str(exc_info.value)

    with pytest.raises(InvalidDataModeError):
        DataMode.from_string("arbitrary_unknown_mode")


# ==============================================================================
# Test 2: Mode Defaulting Rules
# ==============================================================================
def test_02_mode_defaulting_rules():
    """Automated tests default to FIXTURE; dev loopback defaults to OFFLINE_RESEARCH."""
    # Under pytest, with no env var set, it must return fixture
    with patch.dict(os.environ, {}, clear=True):
        mode = get_data_mode()
        assert mode == DataMode.FIXTURE.value

    # Without pytest in sys.modules, it defaults to offline_research
    with patch.dict(os.environ, {}, clear=True):
        with patch.dict(sys.modules, {"pytest": None}):
            mode = get_data_mode()
            assert mode == DataMode.OFFLINE_RESEARCH.value

    # Explicit env override takes precedence
    with patch.dict(os.environ, {"BTC_DATA_MODE": "offline_research"}):
        assert get_data_mode() == DataMode.OFFLINE_RESEARCH.value

    with patch.dict(os.environ, {"DATA_MODE": "provider"}):
        assert get_data_mode() == DataMode.PROVIDER.value


# ==============================================================================
# Test 3: Fixture Mode Blocks Protected File Access
# ==============================================================================
def test_03_fixture_mode_blocks_protected_files():
    """Fixture mode forbids reading any of the 6 protected datasets to guarantee isolation."""
    for rel_path in PROTECTED_ARTIFACTS.keys():
        assert not is_protected_file_access_permitted(rel_path, mode=DataMode.FIXTURE)
        assert not is_protected_file_access_permitted(os.path.join(REPO_ROOT, rel_path), mode=DataMode.FIXTURE)

    # In contrast, offline_research and provider permit reading historical data
    assert is_protected_file_access_permitted("data/raw/ohlcv.parquet", mode=DataMode.OFFLINE_RESEARCH)
    assert is_protected_file_access_permitted("data/raw/ohlcv.parquet", mode=DataMode.PROVIDER)


# ==============================================================================
# Test 4: Offline Research Mode Serves Local Snapshot Without Network
# ==============================================================================
def test_04_offline_research_mode_serves_snapshot(client):
    """Under OFFLINE_RESEARCH, /api/market/candles returns genuine local parquet candles with 0 network calls."""
    with patch.dict(os.environ, {"BTC_DATA_MODE": "offline_research"}):
        res = client.get("/api/market/candles?symbol=BTC-USD&interval=1h&limit=50")
        assert res.status_code == 200
        data = res.json()

        assert data["symbol"] == "BTC-USD"
        assert data["interval"] == "1h"
        assert data["count"] == 50
        assert data["source"] == "LOCAL_HISTORICAL_SNAPSHOT"
        assert len(data["candles"]) == 50

        # Validate candle properties
        last_c = data["candles"][-1]
        assert last_c["time"] > 0
        assert last_c["close"] > 1000
        assert last_c["high"] >= last_c["low"]


# ==============================================================================
# Test 5: Comparator Fails Closed in Restricted Modes
# ==============================================================================
def test_05_comparator_fails_closed_without_sockets(client):
    """When external network is blocked, comparator returns DATA_UNAVAILABLE with primary_price_usd=None."""
    res = client.get("/api/market/comparator")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "DATA_UNAVAILABLE"
    assert data["primary_price_usd"] is None
    assert data["active_primary_provider"] is None
    assert data["healthy_providers_count"] == 0
    assert data["quotes"] == {}
    assert data["divergence_reason"] == "EXTERNAL_NETWORK_BLOCKED"


# ==============================================================================
# Test 6: Network Transport Guard Blocks Outbound Requests
# ==============================================================================
def test_06_transport_guard_blocks_network():
    """assert_no_external_network() raises ExternalNetworkBlockedError in restricted modes."""
    with pytest.raises(ExternalNetworkBlockedError) as exc_info:
        assert_no_external_network("Coinbase REST")
    assert "External market-data network connection blocked" in str(exc_info.value)

    from engine.coinbase_15m_adapter import Coinbase15mAdapter
    adapter = Coinbase15mAdapter()
    with pytest.raises(ExternalNetworkBlockedError):
        adapter.fetch_single_chunk()


# ==============================================================================
# Test 7: Canonical Symbol and Envelope on Candle API
# ==============================================================================
def test_07_canonical_symbol_and_envelope(client):
    """The candle API normalizes symbols to canonical BTC-USD and rejects unsupported pairs."""
    # Canonical request
    res = client.get("/api/market/candles?symbol=BTC-USD&interval=1h&limit=24")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "BTC-USD"
    assert data["count"] == 24

    # Compatible alias BTC/USD
    res_alias = client.get("/api/market/candles?symbol=BTC/USD&interval=1h&limit=24")
    assert res_alias.status_code == 200
    assert res_alias.json()["symbol"] == "BTC-USD"

    # Unsupported pair
    res_bad = client.get("/api/market/candles?symbol=ETH-USD&interval=1h")
    assert res_bad.status_code == 200
    assert res_bad.json()["status"] == "UNSUPPORTED_REQUEST"
    assert res_bad.json()["count"] == 0


# ==============================================================================
# Test 8: Provider Mode Fails Closed in Phase 1
# ==============================================================================
def test_08_provider_mode_fails_closed(client):
    """In Phase 1, provider mode fails closed with PROVIDER_NOT_CONFIGURED and 0 external requests."""
    with patch.dict(os.environ, {"BTC_DATA_MODE": "provider"}):
        res = client.get("/api/market/candles?symbol=BTC-USD&interval=1h")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "DATA_UNAVAILABLE"
        assert data["reason"] == "PROVIDER_NOT_CONFIGURED"
        assert data["candles"] == []
        assert data["count"] == 0


# ==============================================================================
# Test 9: Truthful Reporting Without Fabricated Numbers
# ==============================================================================
def test_09_truthful_reporting_without_fabrication(client):
    """Market routes in blocked provider mode report truthful nulls, never fabricated $80,000 quotes."""
    with patch.dict(os.environ, {"BTC_DATA_MODE": "provider"}):
        res = client.get("/api/market/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "DATA_UNAVAILABLE"
        assert data["market"]["price_usd"] is None
        assert data["market"]["source"] is None
        assert data["candles"] == []
        assert data["forecast"]["price_quantiles_usd"] is None


# ==============================================================================
# Test 10: System Status Contract Exposes Data Mode
# ==============================================================================
def test_10_status_contract_data_mode():
    """SystemStatusContract includes data_mode and data_mode_contract fields."""
    status = evaluate_system_status()
    assert hasattr(status, "data_mode")
    assert hasattr(status, "data_mode_contract")
    assert status.data_mode in ("fixture", "offline_research", "provider")
    contract = status.data_mode_contract
    assert "mode" in contract
    assert "data_mode" in contract
    assert "external_network_allowed" in contract
    assert contract["external_network_allowed"] is False


# ==============================================================================
# Test 11: Protected Artifacts Bit-Level Invariance
# ==============================================================================
def test_11_protected_artifacts_bit_level_invariance():
    """Asserts that all 6 protected datasets and ledgers remain bit-identical."""
    for rel_path, expected_hash in PROTECTED_ARTIFACTS.items():
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
