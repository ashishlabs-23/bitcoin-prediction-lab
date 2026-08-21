"""
research/legacy_direction_audit.py — Audit legacy records with NaN/missing direction
==================================================================================
Identifies any predictions where direction is NaN/NULL or ambiguous, ensuring they
are classified as LEGACY_UNKNOWN_DIRECTION rather than mis-resolved as SKIP wins.
Outputs:
  - results/legacy_direction_audit.csv
"""

import os
import sys
import sqlite3
import csv
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.paths import RESULTS_DIR
from config.database import MARKET_MEMORY_DB_PATH

DB_PATH = MARKET_MEMORY_DB_PATH
CSV_OUTPUT_PATH = os.path.join(RESULTS_DIR, "legacy_direction_audit.csv")

def audit_legacy_direction():
    print("=" * 70)
    print("  LEGACY DIRECTION AUDIT")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT prediction_id, timestamp, price, direction, decision, was_correct, actual_return FROM predictions").fetchall()
    
    audit_rows = []
    nan_count = 0

    for r in rows:
        pid = r["prediction_id"]
        ts = r["timestamp"]
        p = r["price"]
        dir_val = r["direction"]
        dec = r["decision"]
        was_corr = r["was_correct"]
        ret = r["actual_return"]

        is_nan_dir = False
        if dir_val is None or str(dir_val).strip() == "" or str(dir_val).upper() in ["NAN", "NONE", "NULL"]:
            is_nan_dir = True

        if is_nan_dir:
            nan_count += 1
            audit_rows.append({
                "prediction_id": pid,
                "timestamp": ts,
                "price": p,
                "direction": "NaN" if dir_val is None else str(dir_val),
                "decision": dec,
                "was_correct": was_corr,
                "actual_return": ret,
                "classification": "LEGACY_UNKNOWN_DIRECTION",
                "action_taken": "Excluded from directional accuracy calculations"
            })

    with open(CSV_OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["prediction_id", "timestamp", "price", "direction", "decision", "was_correct", "actual_return", "classification", "action_taken"])
        writer.writeheader()
        for r in audit_rows:
            writer.writerow(r)

    print(f"Total predictions checked: {len(rows)}")
    print(f"NaN / ambiguous direction records: {nan_count}")
    print(f"Audit written to: {CSV_OUTPUT_PATH}")

    conn.close()

if __name__ == "__main__":
    audit_legacy_direction()
