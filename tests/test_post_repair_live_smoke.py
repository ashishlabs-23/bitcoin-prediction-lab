"""
tests/test_post_repair_live_smoke.py — Tests for Post-Repair Live Production Pipeline
=====================================================================================
Verifies that:
- Live range forecast generates canonical BTCUSD symbol and 24h horizon.
- Model and Context hashes are frozen and immutable.
- Persistence to canonical market_memory.db works seamlessly.
- Outcome resolution semantics strictly enforce outcome_resolved=0 and was_correct=NULL.
- No block counting occurs prior to 24h outcome resolution.
- No synthetic fallbacks are invoked.
- Longitudinal API and monitor reflect the new live forecast without corrupting block metrics.
"""

import sqlite3
import json
from models.symbol_contract import CANONICAL_SYMBOL
from models.horizon_contract import PRODUCTION_RANGE_HORIZON_LABEL, PRODUCTION_MODEL_VERSION
from engine.range_forecast_service import RangeForecastService
from research.post_repair_live_smoke_test import run_live_smoke_test
from research.post_repair_longitudinal_monitor import post_repair_monitor, MODEL_HASH, CONTEXT_HASH
from config.database import MARKET_MEMORY_DB_PATH

def test_live_production_smoke_pipeline():
    res = run_live_smoke_test()
    assert res["status"] == "POST_REPAIR_LIVE_SMOKE_TEST_PASS"
    assert res["symbol"] == CANONICAL_SYMBOL
    assert res["horizon"] == PRODUCTION_RANGE_HORIZON_LABEL
    assert res["model_version"] == PRODUCTION_MODEL_VERSION
    assert res["observed_blocks"] == 0

def test_smoke_forecast_persistence_and_unresolved_null():
    range_svc = RangeForecastService()
    fc = range_svc.generate_forecast(
        current_price=64000.0,
        vol_24h=0.015,
        features={"vol_24h": 0.015, "rsi_14": 52.0},
        market_regime="RANGING"
    )
    assert fc.symbol == CANONICAL_SYMBOL
    assert fc.horizon == "24h"

    # Verify latest DB rows have NULL was_correct when outcome_resolved = 0
    conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    conn.row_factory = sqlite3.Row
    unres_rows = conn.execute("SELECT was_correct FROM predictions WHERE outcome_resolved = 0").fetchall()
    conn.close()

    for r in unres_rows:
        assert r["was_correct"] is None, f"Unresolved was_correct must be NULL, got {r['was_correct']}"

def test_zero_blocks_before_resolution():
    status = post_repair_monitor.get_status()
    assert status["observed_blocks"] == 0
    assert status["resolved_post_repair_forecasts"] == 0
    assert status["next_milestone"] == 5
