"""
research/synthetic_data_audit.py — Audit all synthetic or simulated prediction records
======================================================================================
Identifies and logs any prediction records in market_memory.db originating from:
- Synthetic feature fallback (e.g. price anchored to ~$115K seed or feature_cache fallback)
- Synthetic Arena simulations (data_source == 'synthetic_arena' or regime LIKE 'SIM_ARENA_%')

Outputs:
  - results/synthetic_data_audit.csv
  - Console summary
"""

import os
import sys
import sqlite3
import csv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.paths import RESULTS_DIR
from config.database import MARKET_MEMORY_DB_PATH

DB_PATH = MARKET_MEMORY_DB_PATH
CSV_OUTPUT_PATH = os.path.join(RESULTS_DIR, "synthetic_data_audit.csv")

def audit_synthetic_data():
    print("=" * 70)
    print("  SYNTHETIC / SIMULATED DATA RECORD AUDIT")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT prediction_id, timestamp, price, regime, data_source FROM predictions").fetchall()
    
    audit_rows = []
    synthetic_count = 0
    
    for r in rows:
        pid = r["prediction_id"]
        ts = r["timestamp"]
        p = float(r["price"])
        reg = str(r["regime"])
        src = str(r["data_source"])
        
        is_synthetic = False
        reason = []
        
        if "synthetic" in src.lower():
            is_synthetic = True
            reason.append(f"data_source '{src}'")
        if reg.startswith("SIM_ARENA_"):
            is_synthetic = True
            reason.append(f"regime '{reg}'")
        if p >= 114000.0 and p <= 116500.0 and ts.startswith("2026"):
            # Potential $115,000 synthetic feature cache fallback
            is_synthetic = True
            reason.append(f"price ${p:,.2f} matches 115k synthetic seed")

        if is_synthetic:
            synthetic_count += 1
            audit_rows.append({
                "record_id": pid,
                "timestamp": ts,
                "source": src,
                "synthetic": True,
                "affected_metrics": "Win Rate, PnL, Calibration",
                "excluded_from_validation": True,
                "reason": " | ".join(reason)
            })

    # Also check stress_trials
    st_rows = conn.execute("SELECT trial_id, timestamp, price, direction, data_source FROM stress_trials").fetchall()
    for r in st_rows:
        tid = r["trial_id"]
        ts = r["timestamp"]
        src = str(r["data_source"])
        audit_rows.append({
            "record_id": tid,
            "timestamp": ts,
            "source": src,
            "synthetic": True,
            "affected_metrics": "Arena Simulation PnL",
            "excluded_from_validation": True,
            "reason": "Stress trial arena simulation"
        })

    with open(CSV_OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["record_id", "timestamp", "source", "synthetic", "affected_metrics", "excluded_from_validation", "reason"])
        writer.writeheader()
        for r in audit_rows:
            writer.writerow(r)

    print(f"Total predictions scanned: {len(rows)}")
    print(f"Synthetic predictions identified: {synthetic_count}")
    print(f"Stress trials identified: {len(st_rows)}")
    print(f"Synthetic audit CSV saved to: {CSV_OUTPUT_PATH}")

    conn.close()

if __name__ == "__main__":
    audit_synthetic_data()
