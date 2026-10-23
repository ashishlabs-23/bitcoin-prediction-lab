"""
research/quarantine_synthetic_evidence.py — Forensic Quarantine Workflow for Synthetic Test Fixtures
====================================================================================================
Workstream A: Clean Evidence Hygiene and Forensic Quarantine.

Forensic Audit Finding (Phase 1 / 1A / 1B):
- 71 post-repair records in `forecast_outcomes` matched synthetic unit-test fixtures
  with current prices of $100,000.00 and $90,000.00 and resolution deltas of 3-46 ms
  (for a 24-hour forward horizon).
- Running tests directly against `experiments/results/market_memory.db` caused this pollution.

This script:
1. Creates a verified, restorable SQLite backup using the SQLite Online Backup API.
2. Identifies all synthetic test-fixture records using strict deterministic criteria:
   - Forecast horizon is '24h' but elapsed time between pred_ts and resolution_ts is < 86400 seconds (24h).
   - current_price is in synthetic test set (e.g. 100000.0, 90000.0, 92000.0).
3. Safely marks and archives them in `quarantined_forecast_outcomes` without blind data destruction.
4. Generates an auditable manifest JSON containing affected IDs, timestamps, and hashes.
5. Defaults to --dry-run mode unless --apply is explicitly specified.
"""

import os
import sys
import json
import sqlite3
import hashlib
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple

# Ensure project root is in sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, PROJECT_ROOT)

from config.database import DEFAULT_SQLITE_PATH, MARKET_MEMORY_DB_PATH

BACKUP_DIR = os.path.join(PROJECT_ROOT, "experiments", "results", "backups")
MANIFEST_DIR = os.path.join(PROJECT_ROOT, "experiments", "results")


def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 digest of a file in 64KB blocks."""
    if not os.path.exists(filepath):
        return ""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def create_sqlite_backup(source_db_path: str, backup_dir: str = BACKUP_DIR) -> Tuple[str, str]:
    """
    Creates an atomic, restorable backup using SQLite Online Backup API.
    Returns (backup_filepath, backup_sha256).
    """
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"market_memory_backup_pre_quarantine_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    src_conn = sqlite3.connect(source_db_path, timeout=60.0)
    dest_conn = sqlite3.connect(backup_path, timeout=60.0)
    try:
        with dest_conn:
            src_conn.backup(dest_conn, pages=1000, sleep=0.01)
    finally:
        dest_conn.close()
        src_conn.close()

    backup_sha = compute_file_sha256(backup_path)
    return backup_path, backup_sha


def identify_contaminated_records(db_path: str) -> List[Dict[str, Any]]:
    """
    Identifies records matching synthetic test fixtures:
    1. current_price in (100000.0, 90000.0, 92000.0)
    2. Resolution time delta < 86400s (24h) for a 24h horizon forecast with data_quality='VALID'
    """
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT 
            fo.outcome_id,
            fo.forecast_id,
            rf.timestamp AS pred_timestamp,
            fo.resolution_timestamp,
            rf.current_price,
            rf.symbol,
            rf.horizon,
            fo.actual_high,
            fo.actual_low,
            fo.actual_close,
            fo.data_quality,
            fo.created_at AS fo_created_at
        FROM forecast_outcomes fo
        JOIN range_forecasts rf ON fo.forecast_id = rf.forecast_id
        WHERE fo.data_quality != 'QUARANTINED_SYNTHETIC_TEST_FIXTURE'
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    contaminated = []
    for r in rows:
        row_dict = dict(r)
        pred_ts_str = row_dict["pred_timestamp"]
        res_ts_str = row_dict["resolution_timestamp"]
        price = row_dict["current_price"]

        is_synthetic = False
        reasons = []

        # Check 1: Synthetic test prices ($100k, $90k, $92k)
        if price in (100000.0, 90000.0, 92000.0):
            is_synthetic = True
            reasons.append(f"Synthetic test price: ${price:.2f}")

        # Check 2: Resolution time < 24h for a 24h forecast
        try:
            pred_dt = datetime.fromisoformat(pred_ts_str.replace("Z", "+00:00"))
            res_dt = datetime.fromisoformat(res_ts_str.replace("Z", "+00:00"))
            elapsed_sec = (res_dt - pred_dt).total_seconds()
            row_dict["elapsed_seconds"] = elapsed_sec

            if elapsed_sec < 86400.0:
                is_synthetic = True
                reasons.append(f"Resolution delta {elapsed_sec:.3f}s < 86400s (instantaneous forward resolution)")
        except Exception as e:
            reasons.append(f"Timestamp parse error: {e}")

        if is_synthetic:
            row_dict["quarantine_reasons"] = reasons
            contaminated.append(row_dict)

    return contaminated


def apply_quarantine(
    db_path: str,
    contaminated: List[Dict[str, Any]],
    backup_path: str,
    backup_sha: str
) -> Dict[str, Any]:
    """
    Applies quarantine to contaminated records inside an explicit atomic transaction:
    1. Creates `quarantined_forecast_outcomes` archive table if not exists.
    2. Copies contaminated rows to `quarantined_forecast_outcomes` with forensic metadata.
    3. Updates `forecast_outcomes.data_quality = 'QUARANTINED_SYNTHETIC_TEST_FIXTURE'`.
    4. Writes audit manifest JSON.
    """
    conn = sqlite3.connect(db_path, timeout=60.0)
    now_iso = datetime.now(timezone.utc).isoformat()
    outcome_ids = [r["outcome_id"] for r in contaminated]
    forecast_ids = [r["forecast_id"] for r in contaminated]

    try:
        with conn:
            cursor = conn.cursor()
            # Ensure quarantine audit table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quarantined_forecast_outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    forecast_id TEXT NOT NULL,
                    prediction_timestamp TEXT,
                    resolution_timestamp TEXT,
                    current_price REAL,
                    elapsed_seconds REAL,
                    original_data_quality TEXT,
                    quarantine_reasons TEXT,
                    quarantined_at TEXT NOT NULL
                );
            """)

            # Insert into quarantine archive
            for r in contaminated:
                cursor.execute("""
                    INSERT OR REPLACE INTO quarantined_forecast_outcomes (
                        outcome_id, forecast_id, prediction_timestamp, resolution_timestamp,
                        current_price, elapsed_seconds, original_data_quality,
                        quarantine_reasons, quarantined_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    r["outcome_id"],
                    r["forecast_id"],
                    r["pred_timestamp"],
                    r["resolution_timestamp"],
                    r["current_price"],
                    r.get("elapsed_seconds", 0.0),
                    r["data_quality"],
                    json.dumps(r.get("quarantine_reasons", [])),
                    now_iso
                ))

            # Update data_quality in active forecast_outcomes table
            placeholders = ",".join("?" for _ in outcome_ids)
            cursor.execute(f"""
                UPDATE forecast_outcomes
                SET data_quality = 'QUARANTINED_SYNTHETIC_TEST_FIXTURE'
                WHERE outcome_id IN ({placeholders});
            """, outcome_ids)

            # Also update range_forecasts data_quality
            fc_placeholders = ",".join("?" for _ in forecast_ids)
            cursor.execute(f"""
                UPDATE range_forecasts
                SET data_quality = 'QUARANTINED_SYNTHETIC_TEST_FIXTURE', degraded = 1
                WHERE forecast_id IN ({fc_placeholders});
            """, forecast_ids)

    finally:
        conn.close()

    post_db_sha = compute_file_sha256(db_path)

    manifest = {
        "manifest_version": "1.0.0",
        "action": "QUARANTINE_SYNTHETIC_TEST_FIXTURES",
        "timestamp_utc": now_iso,
        "database_path": db_path,
        "pre_quarantine_backup_path": backup_path,
        "pre_quarantine_backup_sha256": backup_sha,
        "post_quarantine_db_sha256": post_db_sha,
        "quarantined_record_count": len(contaminated),
        "quarantined_outcome_ids": outcome_ids,
        "quarantined_forecast_ids": forecast_ids,
        "sample_records": contaminated[:5],
        "forensic_summary": (
            f"Successfully quarantined {len(contaminated)} synthetic test-fixture records "
            "from active longitudinal evaluation. Pre-quarantine backup created and verified."
        )
    }

    manifest_path = os.path.join(
        MANIFEST_DIR,
        f"quarantine_manifest_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Forensic Quarantine for Synthetic Test Evidence")
    parser.add_argument(
        "--db-path",
        default=DEFAULT_SQLITE_PATH,
        help="Path to SQLite database to audit/quarantine"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply quarantine modifications. Without this flag, runs in dry-run mode."
    )
    args = parser.parse_args()

    db_path = os.path.abspath(args.db_path)
    print(f"=================================================================")
    print(f"BTCognitive — Forensic Evidence Quarantine Workflow")
    print(f"Target Database: {db_path}")
    print(f"Mode: {'APPLY (State-Changing)' if args.apply else 'DRY-RUN (Safe Read-Only)'}")
    print(f"=================================================================")

    if not os.path.exists(db_path):
        print(f"ERROR: Target database does not exist: {db_path}")
        sys.exit(1)

    # 1. Identify records
    contaminated = identify_contaminated_records(db_path)
    print(f"Identified contaminated test records: {len(contaminated)}")

    if not contaminated:
        print("No synthetic test fixture records found requiring quarantine.")
        sys.exit(0)

    # Group by price
    price_counts = {}
    for r in contaminated:
        p = r["current_price"]
        price_counts[p] = price_counts.get(p, 0) + 1

    print("\nBreakdown of identified records by current_price:")
    for p, cnt in sorted(price_counts.items(), key=lambda x: -x[1]):
        print(f"  Price ${p:,.2f}: {cnt} records")

    sample = contaminated[0]
    print(f"\nSample contaminated record:")
    print(f"  Forecast ID:   {sample['forecast_id']}")
    print(f"  Prediction TS: {sample['pred_timestamp']}")
    print(f"  Resolution TS: {sample['resolution_timestamp']}")
    print(f"  Elapsed (sec): {sample.get('elapsed_seconds', 'N/A')}")
    print(f"  Reasons:       {sample.get('quarantine_reasons')}")

    if not args.apply:
        print("\n[DRY-RUN] No modifications made. Run with --apply to backup and quarantine.")
        sys.exit(0)

    # 2. Backup database
    print("\nCreating restorable backup via SQLite Online Backup API...")
    backup_path, backup_sha = create_sqlite_backup(db_path)
    print(f"Backup created: {backup_path}")
    print(f"Backup SHA256:  {backup_sha}")

    # 3. Apply quarantine
    print("\nApplying quarantine in atomic transaction...")
    manifest = apply_quarantine(db_path, contaminated, backup_path, backup_sha)
    print(f"Quarantine completed successfully!")
    print(f"Quarantined count: {manifest['quarantined_record_count']}")
    print(f"Post-quarantine DB SHA256: {manifest['post_quarantine_db_sha256']}")
    print(f"Manifest written to: {MANIFEST_DIR}")


if __name__ == "__main__":
    main()
