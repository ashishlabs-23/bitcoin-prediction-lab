import json
import sqlite3
import pandas as pd
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_v24_canonical_forecast_manifest():
    """Verify that the authoritative canonical forecast manifest contains the reproduced RMSE values."""
    manifest_path = REPO_ROOT / "experiments" / "results" / "v23_canonical_forecast_manifest.json"
    assert manifest_path.exists(), "Canonical forecast manifest must exist."
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    # 4h persistence RMSE must be $843.34
    res_4h = manifest["tournament_results"]["4h"]["persistence_baseline"]
    assert res_4h["rmse_usd"] == 843.34, f"Expected 4h RMSE 843.34, got {res_4h['rmse_usd']}"
    assert res_4h["mae_usd"] == 560.48, f"Expected 4h MAE 560.48, got {res_4h['mae_usd']}"
    
    # 24h persistence RMSE must be $2073.67
    res_24h = manifest["tournament_results"]["24h"]["persistence_baseline"]
    assert res_24h["rmse_usd"] == 2073.67, f"Expected 24h RMSE 2073.67, got {res_24h['rmse_usd']}"
    assert res_24h["mae_usd"] == 1458.31, f"Expected 24h MAE 1458.31, got {res_24h['mae_usd']}"
    
    # Verdict must be PERSISTENCE_BASELINE_UNBEATEN
    assert manifest["overall_verdict"] == "PERSISTENCE_BASELINE_UNBEATEN"


def test_v24_data_integrity_5622_rows():
    """Verify that both market_memory.db and market_memory.csv have exactly 5622 rows and 0 scored non-directional rows."""
    db_path = REPO_ROOT / "experiments" / "results" / "market_memory.db"
    csv_path = REPO_ROOT / "experiments" / "results" / "market_memory.csv"
    
    assert db_path.exists(), "market_memory.db must exist."
    assert csv_path.exists(), "market_memory.csv must exist."
    
    # SQLite audit
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT prediction_id) FROM predictions")
    db_count, db_distinct = cursor.fetchone()
    
    assert db_count == 5622, f"Expected 5622 DB rows, got {db_count}"
    assert db_distinct == 5622, f"Expected 5622 distinct DB prediction_ids, got {db_distinct}"
    
    cursor.execute("SELECT COUNT(*) FROM predictions WHERE direction IN ('NONE', 'SKIP') AND was_correct IS NOT NULL")
    scored_non_dir_db = cursor.fetchone()[0]
    assert scored_non_dir_db == 0, f"Expected 0 scored non-directional rows in DB, got {scored_non_dir_db}"
    conn.close()
    
    # CSV audit
    df = pd.read_csv(csv_path)
    assert len(df) == 5622, f"Expected 5622 CSV rows, got {len(df)}"
    # ID column in CSV can be id or prediction_id
    id_col = "id" if "id" in df.columns else "prediction_id"
    assert df[id_col].nunique() == 5622, f"Expected 5622 distinct CSV IDs, got {df[id_col].nunique()}"
    
    non_dir_mask = df["direction"].isin(["NONE", "SKIP"])
    scored_non_dir_csv = df[non_dir_mask & df["was_correct"].notna()]
    assert len(scored_non_dir_csv) == 0, f"Expected 0 scored non-directional rows in CSV, got {len(scored_non_dir_csv)}"


def test_v24_pre_reconciliation_backup_exists():
    """Verify that pre-reconciliation backup is preserved on disk with its manifest."""
    backup_dir = REPO_ROOT / "experiments" / "results" / "backups" / "v23_pre_reconciliation_backup"
    assert backup_dir.exists(), "Backup directory must exist."
    assert (backup_dir / "manifest.json").exists(), "Backup manifest.json must exist."
    assert (backup_dir / "market_memory.db").exists(), "Backup market_memory.db must exist."
    assert (backup_dir / "market_memory.csv").exists(), "Backup market_memory.csv must exist."


def test_v24_prospective_ledger_status():
    """Verify prospective forecast ledger integrity and clean non-overlapping block count."""
    ledger_path = REPO_ROOT / "data" / "prospective_forecast_ledger.jsonl"
    assert ledger_path.exists(), "Prospective forecast ledger must exist."
    
    records = []
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))
                
    assert len(records) >= 11, f"Expected at least 11 prospective records, got {len(records)}"
    
    # Verify records have required fields
    for rec in records:
        assert "forecast_id" in rec
        assert "horizon_hours" in rec
        assert "issue_timestamp_utc" in rec
        assert "baseline_predictions" in rec
        assert "challenger_prediction" in rec
        assert "resolution_state" in rec
        
    # Check that 24h clean blocks count < 100 hurdle (status COLLECTING)
    records_24h = [r for r in records if r.get("horizon_hours") == 24 and r.get("resolution_state") == "RESOLVED"]
    assert len(records_24h) < 100, "Prospective evaluation must not prematurely declare 100 clean blocks."


def test_v24_execution_gates_fail_closed():
    """Verify that trade execution and order submission endpoints are disabled and fail closed."""
    # Attempting to post orders must fail (404 Not Found or 405 Method Not Allowed)
    res_orders = client.post("/api/orders", json={"symbol": "BTC-USD", "side": "buy"})
    assert res_orders.status_code in (404, 405), f"Expected 404/405 for /api/orders, got {res_orders.status_code}"
    
    res_trade = client.post("/api/trade", json={"action": "BUY"})
    assert res_trade.status_code in (404, 405), f"Expected 404/405 for /api/trade, got {res_trade.status_code}"
    
    res_paper = client.post("/api/paper/order", json={"amount": 100})
    assert res_paper.status_code in (404, 405), f"Expected 404/405 for /api/paper/order, got {res_paper.status_code}"
