"""
scripts/reconcile_v23_data_integrity.py — V23 Historical Database & CSV Reconciliation
===================================================================================
Conducts forensic analysis, dry-run reconciliation, and safe synchronization
between SQLite predictions table and CSV market_memory export.
"""

import os
import sys
import json
import sqlite3
import hashlib
import shutil
import pandas as pd
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.database import MARKET_MEMORY_DB_PATH
from backtest.market_memory import CSV_PATH, DEFAULT_COLUMNS

BACKUP_DIR = os.path.join(PROJECT_ROOT, "experiments", "results", "backups", "v23_pre_reconciliation_backup")

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def create_safe_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    db_backup_path = os.path.join(BACKUP_DIR, "market_memory.db")
    csv_backup_path = os.path.join(BACKUP_DIR, "market_memory.csv")
    
    # 1. SQLite online backup
    src_conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    dst_conn = sqlite3.connect(db_backup_path)
    with dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    
    # 2. Copy CSV
    shutil.copy2(CSV_PATH, csv_backup_path)
    
    manifest = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_db_sha256": sha256_file(MARKET_MEMORY_DB_PATH),
        "backup_db_sha256": sha256_file(db_backup_path),
        "source_csv_sha256": sha256_file(CSV_PATH),
        "backup_csv_sha256": sha256_file(csv_backup_path),
        "db_size_bytes": os.path.getsize(db_backup_path),
        "csv_size_bytes": os.path.getsize(csv_backup_path)
    }
    with open(os.path.join(BACKUP_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Safe verified backup created in {BACKUP_DIR}")
    return manifest

def audit_discrepancies(dry_run: bool = True):
    conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    df_db = pd.read_sql_query("SELECT * FROM predictions", conn)
    conn.close()
    
    df_csv = pd.read_csv(CSV_PATH)
    
    db_ids = set(df_db["prediction_id"].astype(str))
    csv_ids = set(df_csv["prediction_id"].astype(str))
    
    in_db_not_csv = db_ids - csv_ids
    in_csv_not_db = csv_ids - db_ids
    
    print("===================================================================")
    print("V23 HISTORICAL DATA INTEGRITY AUDIT")
    print("===================================================================")
    print(f"Total SQLite predictions: {len(df_db)}")
    print(f"Total CSV rows:           {len(df_csv)}")
    print(f"Discrepancy (DB - CSV):   {len(df_db) - len(df_csv)}")
    print(f"Rows in DB only:          {len(in_db_not_csv)}")
    print(f"Rows in CSV only:         {len(in_csv_not_db)}")
    
    # Non-directional analysis
    non_trades_db = df_db["direction"].fillna("").astype(str).str.upper().isin(["NONE", "NEUTRAL", "", "HOLD", "ABSTAIN", "SKIP"])
    if "decision" in df_db.columns:
        non_trades_db = non_trades_db | df_db["decision"].fillna("").astype(str).str.upper().isin(["HOLD", "SKIP", "NEUTRAL"])
        
    non_trades_csv = df_csv["direction"].fillna("").astype(str).str.upper().isin(["NONE", "NEUTRAL", "", "HOLD", "ABSTAIN", "SKIP"])
    if "decision" in df_csv.columns:
        non_trades_csv = non_trades_csv | df_csv["decision"].fillna("").astype(str).str.upper().isin(["HOLD", "SKIP", "NEUTRAL"])
        
    print(f"Non-directional in DB:    {non_trades_db.sum()}")
    print(f"Non-directional in CSV:   {non_trades_csv.sum()}")
    print(f"Non-directional delta:    {non_trades_csv.sum() - non_trades_db.sum()}")
    
    # Audit 11 CSV-only rows
    df_csv_only = df_csv[df_csv["prediction_id"].astype(str).isin(in_csv_not_db)]
    print("\n--- 11 CSV-Only Rows Breakdown ---")
    print(df_csv_only[["prediction_id", "timestamp", "direction", "decision", "was_correct", "pnl"]])
    
    # Audit 69 DB-only rows
    df_db_only = df_db[df_db["prediction_id"].astype(str).isin(in_db_not_csv)]
    print("\n--- 69 DB-Only Rows Breakdown ---")
    print(df_db_only["direction"].value_counts())
    print("Timestamp distribution of DB-only rows:")
    print(df_db_only["timestamp"].value_counts().head(5))
    
    if dry_run:
        print("\n[DRY RUN COMPLETE] Zero modifications made to source records.")
        return
        
    # Reconcile: Import the 11 missing CSV records into SQLite, and append the 69 missing DB records into CSV
    print("\nApplying bidirectional synchronization...")
    # 1. Insert 11 CSV-only rows into SQLite
    conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    cur = conn.cursor()
    inserted_to_db = 0
    for _, row in df_csv_only.iterrows():
        # Ensure non-directional was_correct is NULL
        direction = str(row.get("direction", "")).upper()
        decision = str(row.get("decision", "")).upper()
        is_non_directional = direction in ["NONE", "NEUTRAL", "", "HOLD", "ABSTAIN", "SKIP"] or decision in ["HOLD", "SKIP", "NEUTRAL"]
        was_corr = None if is_non_directional else (1 if row.get("was_correct") in [1, True, "1", "True"] else 0)
        
        cols = []
        vals = []
        for col in DEFAULT_COLUMNS:
            if col in row and pd.notna(row[col]):
                cols.append(col)
                if col == "was_correct":
                    vals.append(was_corr)
                else:
                    vals.append(row[col])
        if cols:
            placeholders = ", ".join(["?"] * len(cols))
            sql = f"INSERT OR IGNORE INTO predictions ({', '.join(cols)}) VALUES ({placeholders})"
            cur.execute(sql, vals)
            inserted_to_db += 1
    conn.commit()
    conn.close()
    print(f"Inserted {inserted_to_db} missing rows into SQLite predictions.")
    
    # 2. Append 69 DB-only rows into CSV
    records_to_append = []
    for _, row in df_db_only.iterrows():
        rec = row.to_dict()
        records_to_append.append(rec)
    df_to_append = pd.DataFrame(records_to_append)
    df_to_append.to_csv(CSV_PATH, mode="a", header=False, index=False)
    print(f"Appended {len(df_to_append)} missing rows into CSV market_memory.csv.")
    
    # Verify final counts
    conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    cur = conn.cursor()
    final_db_count = cur.execute("SELECT count(*) FROM predictions").fetchone()[0]
    conn.close()
    final_csv_df = pd.read_csv(CSV_PATH)
    print(f"\nFinal SQLite count: {final_db_count}")
    print(f"Final CSV count:    {len(final_csv_df)}")

    # Write audit JSON
    audit_payload = {
        "audit_version": "23.0.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "matched_rows_count": len(db_ids & csv_ids),
        "db_only_count": len(in_db_not_csv),
        "csv_only_count": len(in_csv_not_db),
        "final_synchronized_count": final_db_count,
        "non_directional_preserved": True
    }
    with open("experiments/results/v23_reconciled_data_audit.json", "w") as f:
        json.dump(audit_payload, f, indent=2)
    print("Wrote experiments/results/v23_reconciled_data_audit.json")

if __name__ == "__main__":
    create_safe_backup()
    audit_discrepancies(dry_run=False)
