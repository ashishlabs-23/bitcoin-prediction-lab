import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.server import app
from engine.smart_entry_engine import SmartEntryDecisionEngine
from engine.probabilistic_entry_engine import ProbabilisticEntryEngine

client = TestClient(app)

PROTECTED_LEDGER_V2 = Path("data/prospective_entry_ledger_v2.jsonl")


def _get_protected_v2_stats():
    if not PROTECTED_LEDGER_V2.exists():
        return 0, "", 0
    content = PROTECTED_LEDGER_V2.read_bytes()
    lines = [line for line in content.split(b"\n") if line.strip()]
    return len(lines), hashlib.sha256(content).hexdigest(), len(content)


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
        "c2_health": "CALIBRATED",
        "user_direction_preference": "AUTO",
    }


def test_1_normal_engine_evaluation_performs_no_ledger_write():
    """1. A normal engine evaluation performs no ledger write and makes zero writer calls."""
    baseline_count, baseline_hash, baseline_size = _get_protected_v2_stats()
    
    with patch.object(ProbabilisticEntryEngine, "log_prospective_decision") as mock_writer:
        engine = SmartEntryDecisionEngine()
        snapshot = _valid_snapshot()
        result = engine.evaluate_market(
            live_price=snapshot["live_price"],
            candles=snapshot["candles"],
            enabled_indicators=snapshot["enabled_indicators"],
            market_snapshot=snapshot["market_snapshot"],
            regime=snapshot["regime"],
            c2_health=snapshot["c2_health"],
            user_direction_preference=snapshot["user_direction_preference"],
        )
        
        mock_writer.assert_not_called()
        assert result["persisted"] is False
        assert result.get("persistence_error") is None
        assert result["status"] == "ABSTAIN"
    
    after_count, after_hash, after_size = _get_protected_v2_stats()
    assert after_count == baseline_count
    assert after_hash == baseline_hash
    assert after_size == baseline_size


def test_2_ordinary_api_request_performs_no_ledger_write():
    """2. An ordinary API request performs no ledger write and makes zero writer calls."""
    baseline_count, baseline_hash, baseline_size = _get_protected_v2_stats()
    
    with patch.object(ProbabilisticEntryEngine, "log_prospective_decision") as mock_writer:
        response = client.post("/api/research/smart-entry", json=_valid_snapshot())
        assert response.status_code == 200
        mock_writer.assert_not_called()
        data = response.json()
        assert data["persisted"] is False
        assert data.get("persistence_error") is None
    
    after_count, after_hash, after_size = _get_protected_v2_stats()
    assert after_count == baseline_count
    assert after_hash == baseline_hash
    assert after_size == baseline_size


def test_3_repeated_evaluation_and_ui_refresh_do_not_append_records():
    """3. Repeated evaluation and UI refresh requests do not append records or invoke writer."""
    baseline_count, baseline_hash, baseline_size = _get_protected_v2_stats()
    
    with patch.object(ProbabilisticEntryEngine, "log_prospective_decision") as mock_writer:
        engine = SmartEntryDecisionEngine()
        snapshot = _valid_snapshot()
        
        # 5 simulated internal engine evaluations
        for _ in range(5):
            res = engine.evaluate_market(
                live_price=snapshot["live_price"],
                candles=snapshot["candles"],
                enabled_indicators=snapshot["enabled_indicators"],
                market_snapshot=snapshot["market_snapshot"],
                regime=snapshot["regime"],
                c2_health=snapshot["c2_health"],
                user_direction_preference=snapshot["user_direction_preference"],
            )
            assert res["persisted"] is False
            
        # 5 simulated UI terminal polling / refresh requests
        for _ in range(5):
            response = client.post("/api/research/smart-entry", json=snapshot)
            assert response.status_code == 200
            assert response.json()["persisted"] is False
            
        mock_writer.assert_not_called()
        
    after_count, after_hash, after_size = _get_protected_v2_stats()
    assert after_count == baseline_count
    assert after_hash == baseline_hash
    assert after_size == baseline_size


def test_4_persistence_disabled_when_opt_in_flag_omitted():
    """4. Persistence remains disabled when opt-in flag is omitted; GET endpoint is write-free."""
    baseline_count, baseline_hash, baseline_size = _get_protected_v2_stats()
    
    # Check engine function signature default
    import inspect
    sig = inspect.signature(SmartEntryDecisionEngine.evaluate_market)
    assert "persist" in sig.parameters
    assert sig.parameters["persist"].default is False
    
    # Check /api/research/entry-quality endpoint signature has NO client-controlled persist parameter
    from api.routes_research import get_entry_quality
    get_sig = inspect.signature(get_entry_quality)
    assert "persist" not in get_sig.parameters
    
    # GET request with or without query params performs zero writes
    with patch.object(ProbabilisticEntryEngine, "log_prospective_decision") as mock_writer:
        response = client.get("/api/research/entry-quality?model_version=v28_meta_rf_v1")
        assert response.status_code == 200
        mock_writer.assert_not_called()
        data = response.json()
        assert data.get("persisted") is False
        
        # Even if a client attempts to pass ?persist=true to GET, no write occurs
        response_attempt = client.get("/api/research/entry-quality?model_version=v28_meta_rf_v1&persist=true")
        assert response_attempt.status_code == 200
        mock_writer.assert_not_called()
        assert response_attempt.json().get("persisted") is False
    
    after_count, after_hash, after_size = _get_protected_v2_stats()
    assert after_count == baseline_count
    assert after_hash == baseline_hash
    assert after_size == baseline_size


def test_5_explicitly_enabled_persistence_isolated_destination(tmp_path):
    """5. Explicitly enabled persistence is only tested against an isolated temporary destination."""
    baseline_count, baseline_hash, baseline_size = _get_protected_v2_stats()
    
    isolated_ledger = tmp_path / "isolated_test_ledger.jsonl"
    assert not isolated_ledger.exists()
    
    engine = SmartEntryDecisionEngine()
    snapshot = _valid_snapshot()
    
    result = engine.evaluate_market(
        live_price=snapshot["live_price"],
        candles=snapshot["candles"],
        enabled_indicators=snapshot["enabled_indicators"],
        market_snapshot=snapshot["market_snapshot"],
        regime=snapshot["regime"],
        c2_health=snapshot["c2_health"],
        user_direction_preference=snapshot["user_direction_preference"],
        persist=True,
        ledger_path=isolated_ledger,
    )
    
    assert result["persisted"] is True
    assert result["persisted_timestamp_utc"] is not None
    assert result.get("persistence_error") is None
    
    # Verify write occurred ONLY in isolated_ledger
    assert isolated_ledger.exists()
    lines = [l for l in isolated_ledger.read_text().split("\n") if l.strip()]
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["action"] == "ABSTAIN"
    assert record["ledger_version"] == "V2_PROSPECTIVE"
    
    # Verify protected ledger is completely untouched
    after_count, after_hash, after_size = _get_protected_v2_stats()
    assert after_count == baseline_count
    assert after_hash == baseline_hash
    assert after_size == baseline_size


def test_6_persistence_failure_fail_closed_honest_representation(tmp_path):
    """6. A persistence failure is represented honestly and cannot change a safe ABSTAIN decision into accepted."""
    baseline_count, baseline_hash, baseline_size = _get_protected_v2_stats()
    
    # Test SmartEntryDecisionEngine with mocked write failure
    engine = SmartEntryDecisionEngine()
    snapshot = _valid_snapshot()
    
    with patch.object(ProbabilisticEntryEngine, "log_prospective_decision", side_effect=IOError("Simulated disk full error")):
        result = engine.evaluate_market(
            live_price=snapshot["live_price"],
            candles=snapshot["candles"],
            enabled_indicators=snapshot["enabled_indicators"],
            market_snapshot=snapshot["market_snapshot"],
            regime=snapshot["regime"],
            c2_health=snapshot["c2_health"],
            user_direction_preference=snapshot["user_direction_preference"],
            persist=True,
            ledger_path=tmp_path / "mocked_fail.jsonl",
        )
        
        # Must fail-closed honestly:
        assert result["persisted"] is False
        assert "Simulated disk full error" in result.get("persistence_error", "")
        # Safe ABSTAIN decision remains intact, NEVER converted into trade acceptance
        assert result["status"] == "ABSTAIN"
        assert result["decision_action"] == "ABSTAIN"
        assert result["candidate"] is None
        assert result["execution_authorization"] == "DISABLED — ANALYSIS ONLY"
        
    after_count, after_hash, after_size = _get_protected_v2_stats()
    assert after_count == baseline_count
    assert after_hash == baseline_hash
    assert after_size == baseline_size


def test_7_existing_decision_and_api_response_contracts_intact():
    """7. Existing decision and API response contracts remain intact across endpoints."""
    baseline_count, baseline_hash, baseline_size = _get_protected_v2_stats()
    
    # Check POST /smart-entry
    response = client.post("/api/research/smart-entry", json=_valid_snapshot())
    assert response.status_code == 200
    data = response.json()
    
    required_keys = [
        "status",
        "instrument",
        "timeframe",
        "decision_action",
        "direction",
        "market_regime",
        "selected_strategy_id",
        "candidate",
        "resolution",
        "first_passage_geometry_baseline",
        "reasons",
        "data_quality_status",
        "execution_authorization",
        "governance_status",
        "persisted",
    ]
    for key in required_keys:
        assert key in data, f"Missing required key: {key}"
        
    assert data["persisted"] is False
    assert data["status"] == "ABSTAIN"
    assert data["decision_action"] == "ABSTAIN"
    assert data["execution_authorization"] == "DISABLED — ANALYSIS ONLY"
    assert data["governance_status"] == "OFFLINE_RESEARCH_ONLY"
    
    # Check GET /entry-quality
    eq_response = client.get("/api/research/entry-quality")
    assert eq_response.status_code == 200
    eq_data = eq_response.json()
    assert eq_data["status"] == "SUCCESS"
    assert eq_data["persisted"] is False
    assert "decision" in eq_data
    assert eq_data["decision"]["action"] in {"ABSTAIN", "ACCEPTED_RESEARCH_CANDIDATE"}
    assert eq_data["decision"]["persisted"] is False
    
    after_count, after_hash, after_size = _get_protected_v2_stats()
    assert after_count == baseline_count
    assert after_hash == baseline_hash
    assert after_size == baseline_size


def test_8_api_endpoints_make_zero_calls_to_ledger_writer():
    """8. Explicit verification that both research endpoints make zero calls to ledger writer."""
    with patch.object(ProbabilisticEntryEngine, "log_prospective_decision") as mock_writer:
        # POST /smart-entry
        r1 = client.post("/api/research/smart-entry", json=_valid_snapshot())
        assert r1.status_code == 200
        
        # GET /entry-quality
        r2 = client.get("/api/research/entry-quality?side=LONG&k_tp=1.5&k_sl=1.0")
        assert r2.status_code == 200
        
        # GET /entry-quality with rogue persist parameter
        r3 = client.get("/api/research/entry-quality?side=SHORT&persist=true")
        assert r3.status_code == 200
        
        # Exact call count verification: must be strictly 0
        assert mock_writer.call_count == 0, f"Expected 0 calls to writer, got {mock_writer.call_count}"
