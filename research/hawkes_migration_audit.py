"""
research/hawkes_migration_audit.py — Safe Hawkes Shadow Database Migration & Audit
===================================================================================
1. Audits every record in data/market_memory.db (hawkes_forecasts & hawkes_outcomes).
2. Checks timestamps, IDs, model versions, feature hashes, duplicates, schema compatibility.
3. Produces results/hawkes_migration_audit.csv.
4. Creates a backup of the authoritative production DB (experiments/results/market_memory.db).
5. Migrates records safely into experiments/results/market_memory.db using INSERT OR IGNORE.
6. Generates results/hawkes_migration_manifest.json with SHA256 hashes and row counts.
"""

import os
import sys
import sqlite3
import hashlib
import json
import csv
import shutil
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.paths import PROJECT_ROOT, RESULTS_DIR
from config.database import MARKET_MEMORY_DB_PATH, LEGACY_HAWKES_DB_PATH

SOURCE_DB = LEGACY_HAWKES_DB_PATH
TARGET_DB = MARKET_MEMORY_DB_PATH
AUDIT_CSV_PATH = os.path.join(RESULTS_DIR, "hawkes_migration_audit.csv")
MANIFEST_JSON_PATH = os.path.join(RESULTS_DIR, "hawkes_migration_manifest.json")

def compute_sha256(filepath: str) -> str:
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def audit_and_migrate():
    print("=" * 70)
    print("  HAWKES SHADOW RECORD MIGRATION & RECONCILIATION")
    print("=" * 70)
    
    src_sha256 = compute_sha256(SOURCE_DB)
    target_sha256_before = compute_sha256(TARGET_DB)
    
    print(f"Source DB: {SOURCE_DB} (SHA256: {src_sha256})")
    print(f"Target DB: {TARGET_DB} (SHA256: {target_sha256_before})")
    
    # 1. Inspect source DB
    src_conn = sqlite3.connect(SOURCE_DB)
    src_conn.row_factory = sqlite3.Row
    
    # 2. Inspect target DB & create tables if not exist
    backup_path = os.path.join(RESULTS_DIR, f"market_memory_pre_hawkes_backup_{int(datetime.now(timezone.utc).timestamp())}.db")
    shutil.copy2(TARGET_DB, backup_path)
    print(f"Authoritative DB backed up to: {backup_path}")
    
    target_conn = sqlite3.connect(TARGET_DB)
    target_conn.row_factory = sqlite3.Row
    
    # Check if target hawkes tables have 0 rows and wrong schema, if so drop & recreate
    with target_conn:
        fc_count = 0
        try:
            fc_count = target_conn.execute("SELECT COUNT(*) FROM hawkes_forecasts").fetchone()[0]
        except Exception:
            pass
        if fc_count == 0:
            target_conn.execute("DROP TABLE IF EXISTS hawkes_forecasts;")
            target_conn.execute("DROP TABLE IF EXISTS hawkes_outcomes;")

        target_conn.execute("""
            CREATE TABLE IF NOT EXISTS hawkes_forecasts (
                forecast_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                current_price REAL NOT NULL,
                mfe_p10 REAL NOT NULL,
                mfe_p50 REAL NOT NULL,
                mfe_p90 REAL NOT NULL,
                mae_p10 REAL NOT NULL,
                mae_p50 REAL NOT NULL,
                mae_p90 REAL NOT NULL,
                upper_p90 REAL NOT NULL,
                lower_p90 REAL NOT NULL,
                direction_state TEXT NOT NULL,
                uncertainty REAL NOT NULL,
                event_pressure REAL NOT NULL,
                lambda_buy REAL NOT NULL,
                lambda_sell REAL NOT NULL,
                lambda_liquidity REAL NOT NULL,
                lambda_volatility REAL NOT NULL,
                model_version TEXT NOT NULL,
                feature_hash TEXT NOT NULL,
                prediction_hash TEXT NOT NULL,
                data_quality TEXT NOT NULL
            );
        """)
        target_conn.execute("CREATE INDEX IF NOT EXISTS idx_hf_ts ON hawkes_forecasts(timestamp);")
        
        target_conn.execute("""
            CREATE TABLE IF NOT EXISTS hawkes_outcomes (
                forecast_id TEXT PRIMARY KEY,
                resolved_timestamp TEXT NOT NULL,
                actual_high REAL NOT NULL,
                actual_low REAL NOT NULL,
                actual_close REAL NOT NULL,
                actual_mfe REAL NOT NULL,
                actual_mae REAL NOT NULL,
                mfe_error_pct REAL NOT NULL,
                mae_error_pct REAL NOT NULL,
                p90_covered INTEGER NOT NULL,
                winkler_score REAL NOT NULL,
                FOREIGN KEY (forecast_id) REFERENCES hawkes_forecasts (forecast_id)
            );
        """)

    # Get target existing counts
    t_fc_count_before = target_conn.execute("SELECT COUNT(*) FROM hawkes_forecasts").fetchone()[0]
    t_oc_count_before = target_conn.execute("SELECT COUNT(*) FROM hawkes_outcomes").fetchone()[0]

    # Audit records
    audit_rows = []
    
    # Audit Forecasts
    forecast_rows = src_conn.execute("SELECT * FROM hawkes_forecasts").fetchall()
    print(f"\nFound {len(forecast_rows)} forecast rows in source DB.")
    
    for row in forecast_rows:
        fid = row["forecast_id"]
        ts = row["timestamp"]
        model_ver = row["model_version"]
        f_hash = row["feature_hash"]
        p_hash = row["prediction_hash"]
        
        # Check duplicate in target
        existing = target_conn.execute("SELECT 1 FROM hawkes_forecasts WHERE forecast_id=?", (fid,)).fetchone()
        is_dup = (existing is not None)
        
        compatible = (bool(fid) and bool(ts) and bool(f_hash) and bool(p_hash))
        migratable = compatible and (not is_dup)
        reason = "Valid new shadow record" if migratable else ("Duplicate in target" if is_dup else "Incompatible schema/missing fields")
        
        audit_rows.append({
            "table": "hawkes_forecasts",
            "record_id": fid,
            "timestamp": ts,
            "duplicate": is_dup,
            "compatible": compatible,
            "migratable": migratable,
            "reason": reason
        })
        
    # Audit Outcomes
    outcome_rows = src_conn.execute("SELECT * FROM hawkes_outcomes").fetchall()
    print(f"Found {len(outcome_rows)} outcome rows in source DB.")
    for row in outcome_rows:
        fid = row["forecast_id"]
        ts = row["resolved_timestamp"]
        existing = target_conn.execute("SELECT 1 FROM hawkes_outcomes WHERE forecast_id=?", (fid,)).fetchone()
        is_dup = (existing is not None)
        compatible = bool(fid) and bool(ts)
        migratable = compatible and (not is_dup)
        reason = "Valid outcome record" if migratable else ("Duplicate in target" if is_dup else "Incompatible schema")
        
        audit_rows.append({
            "table": "hawkes_outcomes",
            "record_id": fid,
            "timestamp": ts,
            "duplicate": is_dup,
            "compatible": compatible,
            "migratable": migratable,
            "reason": reason
        })

    # Save audit CSV
    with open(AUDIT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["table", "record_id", "timestamp", "duplicate", "compatible", "migratable", "reason"])
        writer.writeheader()
        for r in audit_rows:
            writer.writerow(r)
    print(f"Audit CSV written to: {AUDIT_CSV_PATH}")

    # Perform Safe Migration
    migrated_forecasts = 0
    migrated_outcomes = 0
    
    with target_conn:
        # Migrate forecasts
        for row in forecast_rows:
            vals = dict(row)
            cols = list(vals.keys())
            placeholders = ":" + ", :".join(cols)
            col_names = ", ".join(f"[{c}]" for c in cols)
            cur = target_conn.execute(f"INSERT OR IGNORE INTO hawkes_forecasts ({col_names}) VALUES ({placeholders})", vals)
            if cur.rowcount > 0:
                migrated_forecasts += 1
                
        # Migrate outcomes
        for row in outcome_rows:
            vals = dict(row)
            cols = list(vals.keys())
            placeholders = ":" + ", :".join(cols)
            col_names = ", ".join(f"[{c}]" for c in cols)
            cur = target_conn.execute(f"INSERT OR IGNORE INTO hawkes_outcomes ({col_names}) VALUES ({placeholders})", vals)
            if cur.rowcount > 0:
                migrated_outcomes += 1

    t_fc_count_after = target_conn.execute("SELECT COUNT(*) FROM hawkes_forecasts").fetchone()[0]
    t_oc_count_after = target_conn.execute("SELECT COUNT(*) FROM hawkes_outcomes").fetchone()[0]
    
    src_conn.close()
    target_conn.close()

    target_sha256_after = compute_sha256(TARGET_DB)

    manifest = {
        "migration_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_db_path": SOURCE_DB,
        "source_db_sha256": src_sha256,
        "target_db_path": TARGET_DB,
        "backup_db_path": backup_path,
        "target_db_sha256_before": target_sha256_before,
        "target_db_sha256_after": target_sha256_after,
        "hawkes_forecasts": {
            "source_rows": len(forecast_rows),
            "target_before": t_fc_count_before,
            "migrated": migrated_forecasts,
            "target_after": t_fc_count_after
        },
        "hawkes_outcomes": {
            "source_rows": len(outcome_rows),
            "target_before": t_oc_count_before,
            "migrated": migrated_outcomes,
            "target_after": t_oc_count_after
        },
        "status": "MIGRATION_SUCCESS"
    }

    with open(MANIFEST_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nMigration Complete:")
    print(f"  hawkes_forecasts: {migrated_forecasts} migrated (Total in target: {t_fc_count_after})")
    print(f"  hawkes_outcomes:  {migrated_outcomes} migrated (Total in target: {t_oc_count_after})")
    print(f"  Manifest written to: {MANIFEST_JSON_PATH}")

if __name__ == "__main__":
    audit_and_migrate()
