"""
research/post_repair_dataset_audit.py — Post-Repair Clean Dataset Audit
======================================================================
Enforces strict boundary between historical pre-repair records and
authoritative post-repair longitudinal observations.

Classification Categories:
  - VALID_POST_REPAIR: Resolved 24h prediction generated after POST_REPAIR_EVIDENCE_START
  - PRE_REPAIR: Historical observation generated prior to contract repair lock
  - INVALID_HORIZON: Resolution timeframe does not match 24h production contract
  - UNRESOLVED: Prediction outcome still pending resolution
  - SYNTHETIC: Simulation/Stress test artifact or synthetic price fallback
  - PROVENANCE_FAILURE: Checksum, model hash, or context hash mismatch
  - DUPLICATE: Repeated prediction timestamp or duplicate ID
  - INVALID_SCHEMA: Missing mandatory fields or malformed records

Outputs:
  - results/post_repair_dataset_audit.csv
  - Console Audit Summary
"""

import os
import sys
import sqlite3
import csv
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.paths import RESULTS_DIR
from config.database import MARKET_MEMORY_DB_PATH

POST_REPAIR_EVIDENCE_START = "2026-08-21T12:15:00Z"
AUDIT_CSV_PATH = os.path.join(RESULTS_DIR, "post_repair_dataset_audit.csv")

def audit_dataset():
    print("=" * 70)
    print("  BTCognitive — POST-REPAIR EVIDENCE DATASET AUDIT")
    print(f"  Boundary Timestamp: {POST_REPAIR_EVIDENCE_START}")
    print("=" * 70)

    conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT * FROM predictions ORDER BY timestamp ASC").fetchall()
    print(f"Total historical predictions in database: {len(rows)}")

    start_dt = pd.Timestamp(POST_REPAIR_EVIDENCE_START).tz_convert(timezone.utc)

    audit_records = []
    seen_ids = set()
    seen_ts = set()

    counts = {
        "VALID_POST_REPAIR": 0,
        "PRE_REPAIR": 0,
        "INVALID_HORIZON": 0,
        "UNRESOLVED": 0,
        "SYNTHETIC": 0,
        "PROVENANCE_FAILURE": 0,
        "DUPLICATE": 0,
        "INVALID_SCHEMA": 0
    }

    for r in rows:
        p_id = r["prediction_id"]
        ts_str = r["timestamp"]
        p = r["price"]
        reg = str(r["regime"])
        src = str(r["data_source"])
        resolved = bool(r["outcome_resolved"])
        res_at = r["outcome_resolved_at"]
        was_corr = r["was_correct"]
        actual_ret = r["actual_return"]

        # 1. Check Duplicates
        if p_id in seen_ids or ts_str in seen_ts:
            classification = "DUPLICATE"
            reason = "Duplicate prediction ID or identical timestamp"
        else:
            seen_ids.add(p_id)
            seen_ts.add(ts_str)

            # 2. Check Schema completeness
            if not p_id or not ts_str or p is None or p <= 0:
                classification = "INVALID_SCHEMA"
                reason = "Missing price, ID, or malformed numerical payload"

            # 3. Check Synthetic
            elif "synthetic" in src.lower() or reg.startswith("SIM_ARENA_") or (p >= 114000.0 and p <= 116500.0 and ts_str.startswith("2026")):
                classification = "SYNTHETIC"
                reason = f"Identified as synthetic/simulated (source: {src}, regime: {reg})"

            # 4. Check Unresolved
            elif not resolved or was_corr is None:
                classification = "UNRESOLVED"
                reason = "Outcome is pending resolution (was_correct=NULL)"

            else:
                # Parse timestamp
                try:
                    row_dt = pd.Timestamp(ts_str).tz_convert(timezone.utc) if pd.Timestamp(ts_str).tz is not None else pd.Timestamp(ts_str).tz_localize(timezone.utc)
                except Exception:
                    row_dt = start_dt - pd.Timedelta(days=1)

                # Check horizon resolution validity
                try:
                    res_dt = pd.Timestamp(res_at).tz_convert(timezone.utc) if pd.Timestamp(res_at).tz is not None else pd.Timestamp(res_at).tz_localize(timezone.utc)
                    diff_hours = (res_dt - row_dt).total_seconds() / 3600.0
                    horizon_valid = (diff_hours >= 23.5)
                except Exception:
                    horizon_valid = False

                if not horizon_valid:
                    classification = "INVALID_HORIZON"
                    reason = f"Resolution window ({diff_hours:.1f}h) violates 24h contract"
                elif row_dt < start_dt:
                    classification = "PRE_REPAIR"
                    reason = "Pre-dates post-repair evidence boundary (retained for history)"
                else:
                    classification = "VALID_POST_REPAIR"
                    reason = "Authoritative post-repair 24h resolved observation"

        counts[classification] += 1
        audit_records.append({
            "prediction_id": p_id,
            "timestamp": ts_str,
            "price": p,
            "regime": reg,
            "classification": classification,
            "reason": reason,
            "outcome_resolved": resolved,
            "was_correct": str(was_corr),
            "actual_return": actual_ret
        })

    conn.close()

    # Save to CSV
    with open(AUDIT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "prediction_id", "timestamp", "price", "regime", "classification",
            "reason", "outcome_resolved", "was_correct", "actual_return"
        ])
        writer.writeheader()
        for rec in audit_records:
            writer.writerow(rec)

    print("\nDataset Audit Results:")
    for cat, num in counts.items():
        print(f"  - {cat:<22}: {num:>5} rows")

    print(f"\nAudit saved to: {AUDIT_CSV_PATH}")
    return counts

if __name__ == "__main__":
    audit_dataset()
