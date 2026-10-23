import json
import math
import numpy as np
import pandas as pd
from pathlib import Path
import pytest
from scipy import stats
from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)
REPO_ROOT = Path(__file__).resolve().parent.parent


def test_v25_strategy_turnover_units_and_friction():
    """Verify that strategy turnover units correctly distinguish 1-step transitions from 2-step reversals."""
    # Simulation: [0 -> 1 -> -1 -> 1 -> 0]
    # Positions: 0, 1, -1, 1, 0
    # Transitions:
    # 0 -> 1: +1 unit (1-step entry)
    # 1 -> -1: 2 units (reversal)
    # -1 -> 1: 2 units (reversal)
    # 1 -> 0: +1 unit (1-step exit)
    # Total events: 4
    # Total turnover units: 1 + 2 + 2 + 1 = 6 units
    # Total completed round trips: 6 / 2 = 3.0
    # Friction @ 87 bps: 6 * 43.5 = 261.0 bps
    positions = np.array([0, 1, -1, 1, 0])
    pos_changes = np.abs(np.diff(positions, prepend=0))
    
    event_count = int(np.sum(pos_changes > 0))
    turnover_units = float(np.sum(pos_changes))
    reversals = int(np.sum(pos_changes == 2))
    one_steps = int(np.sum(pos_changes == 1))
    
    assert event_count == 4
    assert reversals == 2
    assert one_steps == 2
    assert turnover_units == 6.0
    
    cost_round_trip = 87.0
    friction_bps = turnover_units * (cost_round_trip / 2.0)
    assert friction_bps == 261.0


def test_v25_canonical_strategy_manifest():
    """Verify that v25_canonical_strategy_manifest.json reflects standardized turnover and zero-exposure victory."""
    manifest_path = REPO_ROOT / "experiments" / "results" / "v25_canonical_strategy_manifest.json"
    assert manifest_path.exists(), "v25_canonical_strategy_manifest.json must exist."
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    matrix = manifest["standardized_performance_matrix"]
    assert matrix["NO_TRADE_BENCHMARK"]["net_return_bps"] == 0.0
    assert matrix["NO_TRADE_BENCHMARK"]["verdict"] == "DECISIVE_WINNER"
    
    dual_sma = matrix["TS_MOM_TREND"]
    assert dual_sma["signal_events"] == 100
    assert dual_sma["reversals"] == 99
    assert dual_sma["turnover_units"] == 199.0
    assert dual_sma["total_friction_bps"] == 8656.5
    assert dual_sma["net_return_bps"] < 0
    assert manifest["governance_verdict"] == "NO_STRATEGY_WINNER_ESTABLISHED"


def test_v25_forecast_clark_west_and_dm_statistics():
    """Verify that Clark-West nested model test statistics are negative for all horizons."""
    manifest_path = REPO_ROOT / "experiments" / "results" / "v25_canonical_forecast_manifest.json"
    assert manifest_path.exists(), "v25_canonical_forecast_manifest.json must exist."
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    for horizon in ["1h", "4h", "24h"]:
        h_data = manifest["canonical_metrics"][horizon]["ridge_l2_challenger"]
        assert h_data["dm_hln_stat"] < 0, f"DM-HLN stat must be negative for {horizon}"
        assert h_data["clark_west_stat"] < 0, f"Clark-West stat must be negative for {horizon}"
        assert h_data["clark_west_p_value_one_sided"] > 0.50, f"CW p-value must exceed 0.50 for {horizon}"
        assert h_data["statistically_superior_to_persistence"] is False


def test_v25_prospective_ledger_contract_freeze():
    """Verify prospective forecast ledger integrity and structure."""
    ledger_path = REPO_ROOT / "data" / "prospective_forecast_ledger.jsonl"
    assert ledger_path.exists(), "Prospective forecast ledger must exist."
    
    records = []
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))
                
    assert len(records) >= 11
    for r in records:
        assert "forecast_id" in r
        assert "target_name" in r
        assert "horizon_hours" in r
        assert "resolution_state" in r
        
    # Check that clean mature 24h blocks count is under 100 hurdle
    mature_24h = [r for r in records if r.get("horizon_hours") == 24 and r.get("resolution_state") == "RESOLVED"]
    assert len(mature_24h) < 100


def test_v25_execution_gates_fail_closed():
    """Verify that execution endpoints return HTTP 404/405 fail-closed."""
    res_orders = client.post("/api/orders", json={"symbol": "BTC-USD", "side": "buy"})
    assert res_orders.status_code in (404, 405)
    
    res_trade = client.post("/api/trade", json={"action": "BUY"})
    assert res_trade.status_code in (404, 405)
    
    res_paper = client.post("/api/paper/order", json={"amount": 100})
    assert res_paper.status_code in (404, 405)
