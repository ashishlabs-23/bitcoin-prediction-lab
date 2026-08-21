"""
research/market_memory_reconciliation.py
=========================================
Audits and reconciles the two discovered market_memory.db instances:
  1. data/market_memory.db           (hawkes_shadow_session legacy path)
  2. experiments/results/market_memory.db  (production canonical path)

Outputs:
  - Console report (tables, row counts, latest timestamps, schema diff)
  - results/market_memory_reconciliation.csv  (record-level audit)
  - results/market_memory_migration.sql       (append-only migration if needed)

DO NOT delete or overwrite either DB. This is a read-only audit + migration plan.
"""

import os
import sys
import sqlite3
import hashlib
import csv
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB1_PATH = os.path.join(ROOT_DIR, "data", "market_memory.db")
DB2_PATH = os.path.join(ROOT_DIR, "experiments", "results", "market_memory.db")
OUTPUT_DIR = os.path.join(ROOT_DIR, "experiments", "results")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def db_info(path: str) -> dict:
    """Returns table names, row counts, schema, and latest timestamps for each table."""
    info = {"path": path, "exists": os.path.exists(path), "tables": {}}
    if not info["exists"]:
        return info
    size_bytes = os.path.getsize(path)
    info["size_bytes"] = size_bytes
    try:
        conn = sqlite3.connect(path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        tables = [r[0] for r in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )]
        for tbl in tables:
            tbl_info = {}
            try:
                count = cursor.execute(f"SELECT COUNT(*) FROM [{tbl}]").fetchone()[0]
                tbl_info["row_count"] = count
            except Exception as e:
                tbl_info["row_count"] = f"ERROR: {e}"

            # Try to get schema
            try:
                schema_rows = cursor.execute(
                    f"SELECT sql FROM sqlite_master WHERE name=?", (tbl,)
                ).fetchone()
                tbl_info["schema"] = schema_rows[0] if schema_rows else ""
            except Exception:
                tbl_info["schema"] = ""

            # Try to get latest timestamp
            try:
                ts_col = None
                cols = [r[1] for r in cursor.execute(f"PRAGMA table_info([{tbl}])")]
                for candidate in ["timestamp", "created_at", "resolved_at"]:
                    if candidate in cols:
                        ts_col = candidate
                        break
                if ts_col:
                    result = cursor.execute(
                        f"SELECT MAX([{ts_col}]) FROM [{tbl}]"
                    ).fetchone()
                    tbl_info["latest_timestamp"] = result[0] if result else None
                else:
                    tbl_info["latest_timestamp"] = None
                tbl_info["columns"] = cols
            except Exception as e:
                tbl_info["latest_timestamp"] = f"ERROR: {e}"
                tbl_info["columns"] = []

            info["tables"][tbl] = tbl_info
        conn.close()
    except Exception as e:
        info["error"] = str(e)
    return info


def compute_db_hash(path: str) -> str:
    """SHA256 of the DB file bytes."""
    if not os.path.exists(path):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def find_orphan_hawkes_records(db1_conn, db2_conn) -> list:
    """
    Finds hawkes_forecasts / hawkes_outcomes rows in DB1 that are NOT in DB2.
    Returns list of dicts describing orphan records.
    """
    orphans = []
    for tbl in ("hawkes_forecasts", "hawkes_outcomes"):
        try:
            rows1 = {r[0] for r in db1_conn.execute(
                f"SELECT forecast_id FROM [{tbl}]"
            )}
        except Exception:
            rows1 = set()
        try:
            rows2 = {r[0] for r in db2_conn.execute(
                f"SELECT forecast_id FROM [{tbl}]"
            )}
        except Exception:
            rows2 = set()
        only_in_db1 = rows1 - rows2
        for fid in sorted(only_in_db1):
            orphans.append({"table": tbl, "forecast_id": fid, "source_db": "data/market_memory.db"})
    return orphans


def generate_migration_sql(db1_conn, orphans: list) -> list:
    """Generates INSERT OR IGNORE SQL statements for orphan records."""
    stmts = []
    for record in orphans:
        tbl = record["table"]
        fid = record["forecast_id"]
        try:
            row = db1_conn.execute(
                f"SELECT * FROM [{tbl}] WHERE forecast_id=?", (fid,)
            ).fetchone()
            if row:
                cols = [d[0] for d in db1_conn.execute(f"SELECT * FROM [{tbl}] LIMIT 1").description]
                vals = tuple(row)
                placeholders = ", ".join(["?" for _ in cols])
                col_str = ", ".join(f"[{c}]" for c in cols)
                # Generate INSERT OR IGNORE
                val_literals = []
                for v in vals:
                    if v is None:
                        val_literals.append("NULL")
                    elif isinstance(v, str):
                        escaped = v.replace("'", "''")
                        val_literals.append(f"'{escaped}'")
                    else:
                        val_literals.append(str(v))
                val_str = ", ".join(val_literals)
                stmts.append(
                    f"INSERT OR IGNORE INTO [{tbl}] ({col_str}) VALUES ({val_str});"
                )
        except Exception as e:
            stmts.append(f"-- ERROR generating migration for {tbl}/{fid}: {e}")
    return stmts


def main():
    print("=" * 70)
    print("  BTCognitive — Market Memory Reconciliation Audit")
    print(f"  Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    print(f"\n[1] DB1 (legacy/data): {DB1_PATH}")
    print(f"[2] DB2 (production):  {DB2_PATH}")

    info1 = db_info(DB1_PATH)
    info2 = db_info(DB2_PATH)

    hash1 = compute_db_hash(DB1_PATH)
    hash2 = compute_db_hash(DB2_PATH)

    print(f"\n--- DB1 ---")
    print(f"  Exists:    {info1['exists']}")
    print(f"  Size:      {info1.get('size_bytes', 'N/A')} bytes")
    print(f"  SHA256:    {hash1}")
    if "error" in info1:
        print(f"  ERROR:     {info1['error']}")
    for tbl, ti in info1.get("tables", {}).items():
        print(f"  Table: {tbl}")
        print(f"    rows:    {ti.get('row_count', '?')}")
        print(f"    latest:  {ti.get('latest_timestamp', '?')}")

    print(f"\n--- DB2 ---")
    print(f"  Exists:    {info2['exists']}")
    print(f"  Size:      {info2.get('size_bytes', 'N/A')} bytes")
    print(f"  SHA256:    {hash2}")
    if "error" in info2:
        print(f"  ERROR:     {info2['error']}")
    for tbl, ti in info2.get("tables", {}).items():
        print(f"  Table: {tbl}")
        print(f"    rows:    {ti.get('row_count', '?')}")
        print(f"    latest:  {ti.get('latest_timestamp', '?')}")

    # Table comparison
    tables1 = set(info1.get("tables", {}).keys())
    tables2 = set(info2.get("tables", {}).keys())
    only_in_1 = tables1 - tables2
    only_in_2 = tables2 - tables1
    common = tables1 & tables2

    print(f"\n--- Table Comparison ---")
    print(f"  Common tables:      {sorted(common)}")
    print(f"  Only in DB1:        {sorted(only_in_1)}")
    print(f"  Only in DB2:        {sorted(only_in_2)}")

    # Determination
    print(f"\n--- Authoritative DB Determination ---")
    db2_preds = info2.get("tables", {}).get("predictions", {}).get("row_count", 0) or 0
    db1_preds = info1.get("tables", {}).get("predictions", {}).get("row_count", 0) or 0
    print(f"  DB2 (production) predictions rows: {db2_preds}")
    print(f"  DB1 (legacy data) predictions rows: {db1_preds}")

    if db2_preds >= db1_preds:
        print("  VERDICT: DB2 (experiments/results/market_memory.db) is AUTHORITATIVE")
        print("           DB1 (data/market_memory.db) is LEGACY/SHADOW-ONLY")
    else:
        print("  VERDICT: WARNING — DB1 has MORE records than DB2. Manual review required.")

    # Orphan hawkes records
    orphans = []
    if info1["exists"] and info2["exists"]:
        try:
            db1_conn = sqlite3.connect(DB1_PATH, timeout=5.0)
            db1_conn.row_factory = sqlite3.Row
            db2_conn = sqlite3.connect(DB2_PATH, timeout=5.0)
            db2_conn.row_factory = sqlite3.Row

            orphans = find_orphan_hawkes_records(db1_conn, db2_conn)
            print(f"\n--- Hawkes Orphan Records ---")
            print(f"  Records in DB1 not in DB2: {len(orphans)}")
            for o in orphans[:10]:
                print(f"    {o['table']}: {o['forecast_id']}")
            if len(orphans) > 10:
                print(f"    ... and {len(orphans)-10} more")

            # Write migration SQL
            if orphans:
                sql_stmts = generate_migration_sql(db1_conn, orphans)
                migration_path = os.path.join(OUTPUT_DIR, "market_memory_migration.sql")
                with open(migration_path, "w") as f:
                    f.write("-- Market Memory Orphan Record Migration (append-only)\n")
                    f.write(f"-- Generated: {datetime.now(timezone.utc).isoformat()}\n")
                    f.write(f"-- Source: {DB1_PATH}\n")
                    f.write(f"-- Target: {DB2_PATH}\n\n")
                    for stmt in sql_stmts:
                        f.write(stmt + "\n")
                print(f"\n  Migration SQL written to: {migration_path}")
            else:
                print("  No orphan records requiring migration.")

            db1_conn.close()
            db2_conn.close()
        except Exception as e:
            print(f"  ERROR during orphan check: {e}")

    # Write CSV audit
    csv_path = os.path.join(OUTPUT_DIR, "market_memory_reconciliation.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "db", "table", "row_count", "latest_timestamp", "columns"
        ])
        writer.writeheader()
        for db_label, info in [("data/market_memory.db", info1),
                                 ("experiments/results/market_memory.db", info2)]:
            for tbl, ti in info.get("tables", {}).items():
                writer.writerow({
                    "db": db_label,
                    "table": tbl,
                    "row_count": ti.get("row_count", ""),
                    "latest_timestamp": ti.get("latest_timestamp", ""),
                    "columns": "|".join(ti.get("columns", []))
                })

    print(f"\n  Reconciliation CSV: {csv_path}")
    print("\n[DONE] Market Memory Reconciliation complete.")
    print("  NEXT STEP: Review migration SQL before running on production DB.")
    print("  DO NOT delete data/market_memory.db until migration is verified.")


if __name__ == "__main__":
    main()
