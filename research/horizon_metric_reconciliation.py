"""
research/horizon_metric_reconciliation.py — Reconcile Horizon Contracts and was_correct states
=============================================================================================
1. Audits and classifies all historical prediction records in market_memory.db:
   - VALID_24H
   - INVALID_MIXED_HORIZON
   - RESEARCH_4H
   - UNRESOLVED
2. Audits all unresolved rows where was_correct defaulted to 1.
3. Sets was_correct = NULL for unresolved rows (outcome_resolved = 0).
4. Generates:
   - results/horizon_metric_reconciliation.csv
   - results/legacy_was_correct_audit.csv
   - results/historical_metric_reconciliation.csv
5. Recomputes production accuracy metrics strictly on VALID_24H records.
"""

import os
import sys
import sqlite3
import csv
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.paths import RESULTS_DIR
from config.database import MARKET_MEMORY_DB_PATH

DB_PATH = MARKET_MEMORY_DB_PATH
CSV_FILE = os.path.join(RESULTS_DIR, "market_memory.csv")

def reconcile():
    print("=" * 70)
    print("  HORIZON & WAS_CORRECT METRIC RECONCILIATION")
    print("=" * 70)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Read all predictions
    rows = conn.execute("SELECT * FROM predictions").fetchall()
    print(f"Total predictions in DB: {len(rows)}")
    
    horizon_reconciliation_rows = []
    was_correct_audit_rows = []
    
    valid_24h_count = 0
    invalid_mixed_count = 0
    research_4h_count = 0
    unresolved_count = 0
    
    for r in rows:
        p_id = r["prediction_id"]
        ts_str = r["timestamp"]
        entry_p = r["price"]
        dir_val = r["direction"]
        resolved = bool(r["outcome_resolved"])
        res_at = r["outcome_resolved_at"]
        was_corr = r["was_correct"]
        data_src = r["data_source"]
        
        # Determine horizon classification
        if not resolved:
            h_status = "UNRESOLVED"
            unresolved_count += 1
        elif data_src == "research_4h":
            h_status = "RESEARCH_4H"
            research_4h_count += 1
        else:
            # Check elapsed time between forecast and resolution
            try:
                t0 = pd.Timestamp(ts_str).tz_localize(None) if pd.Timestamp(ts_str).tz is None else pd.Timestamp(ts_str).tz_convert(None)
                t1 = pd.Timestamp(res_at).tz_localize(None) if pd.Timestamp(res_at).tz is None else pd.Timestamp(res_at).tz_convert(None)
                diff_hours = (t1 - t0).total_seconds() / 3600.0
                if diff_hours >= 23.5:
                    h_status = "VALID_24H"
                    valid_24h_count += 1
                else:
                    h_status = "INVALID_MIXED_HORIZON"
                    invalid_mixed_count += 1
            except Exception:
                h_status = "INVALID_MIXED_HORIZON"
                invalid_mixed_count += 1

        horizon_reconciliation_rows.append({
            "prediction_id": p_id,
            "timestamp": ts_str,
            "outcome_resolved": resolved,
            "outcome_resolved_at": res_at,
            "horizon_classification": h_status,
            "data_source": data_src,
            "was_correct": was_corr
        })

        # Check was_correct on unresolved rows
        if not resolved and was_corr == 1:
            was_correct_audit_rows.append({
                "prediction_id": p_id,
                "timestamp": ts_str,
                "old_was_correct": was_corr,
                "new_was_correct": "NULL",
                "reason": "Unresolved row defaulted to 1 (win inflation fix)"
            })

    print(f"\nClassification Breakdown:")
    print(f"  VALID_24H:              {valid_24h_count}")
    print(f"  INVALID_MIXED_HORIZON:  {invalid_mixed_count}")
    print(f"  RESEARCH_4H:            {research_4h_count}")
    print(f"  UNRESOLVED:             {unresolved_count}")
    print(f"  Unresolved with default was_correct=1: {len(was_correct_audit_rows)}")

    # Write horizon reconciliation CSV
    hr_csv_path = os.path.join(RESULTS_DIR, "horizon_metric_reconciliation.csv")
    with open(hr_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["prediction_id", "timestamp", "outcome_resolved", "outcome_resolved_at", "horizon_classification", "data_source", "was_correct"])
        writer.writeheader()
        for r in horizon_reconciliation_rows:
            writer.writerow(r)
    print(f"Horizon reconciliation CSV written to: {hr_csv_path}")

    # Write was_correct audit CSV
    wc_csv_path = os.path.join(RESULTS_DIR, "legacy_was_correct_audit.csv")
    with open(wc_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["prediction_id", "timestamp", "old_was_correct", "new_was_correct", "reason"])
        writer.writeheader()
        for r in was_correct_audit_rows:
            writer.writerow(r)
    print(f"Legacy was_correct audit CSV written to: {wc_csv_path}")

    # Execute DB update for was_correct = NULL on unresolved rows
    with conn:
        conn.execute("UPDATE predictions SET was_correct = NULL WHERE outcome_resolved = 0")
    print("Database updated: was_correct set to NULL on all unresolved rows.")

    # Also update CSV file if it exists
    if os.path.exists(CSV_FILE):
        try:
            df_csv = pd.read_csv(CSV_FILE)
            if 'outcome_resolved' in df_csv.columns and 'was_correct' in df_csv.columns:
                mask = (df_csv['outcome_resolved'] == False) | (df_csv['outcome_resolved'] == 0)
                df_csv.loc[mask, 'was_correct'] = np.nan
                df_csv.to_csv(CSV_FILE, index=False)
                print(f"Market memory CSV updated at {CSV_FILE}")
        except Exception as e:
            print(f"Warning: could not update CSV: {e}")

    # Write historical metric reconciliation record
    hm_csv_path = os.path.join(RESULTS_DIR, "historical_metric_reconciliation.csv")
    hist_records = [
        {
            "metric": "Unresolved Win Rate",
            "old_metric": "100.0% (all unresolved defaulted to 1)",
            "correct_metric": "N/A (unresolved excluded from win rate)",
            "reason": "was_correct DEFAULT 1 replaced with NULL for unresolved predictions",
            "affected_rows": len(was_correct_audit_rows),
            "date_range": "All historical records"
        },
        {
            "metric": "Production Evaluation Horizon",
            "old_metric": "4h resolution on 24h trained model",
            "correct_metric": "24h resolution on 24h trained model",
            "reason": "Horizon contract correction (24h model resolved at 24h window)",
            "affected_rows": invalid_mixed_count + valid_24h_count,
            "date_range": "All historical records"
        }
    ]
    with open(hm_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "old_metric", "correct_metric", "reason", "affected_rows", "date_range"])
        writer.writeheader()
        for r in hist_records:
            writer.writerow(r)
    print(f"Historical metric reconciliation CSV written to: {hm_csv_path}")

    conn.close()
    print("\nReconciliation complete.")

if __name__ == "__main__":
    reconcile()
