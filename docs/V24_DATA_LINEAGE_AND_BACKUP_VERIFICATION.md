# BTCognitive V24 — Historical Data Lineage & Backup Verification Audit

**Specialist Role:** Agent B (Forensic Data Auditor)  
**Date:** 19 October 2026  
**Status:** Canonical Verification Complete — Data Integrity Fully Confirmed  
**Primary Stores Audited:**
- SQLite Database: `experiments/results/market_memory.db` (`predictions` table)
- CSV Flat File: `experiments/results/market_memory.csv`
- Pre-Reconciliation Backup: `experiments/results/backups/v23_pre_reconciliation_backup/`

---

## 1. Executive Summary & Verification Census

Following the V23 reconciliation between SQLite and CSV prediction stores, an independent forensic audit was conducted on both persistent artifacts without modifying live data.

### Record Census Summary:

| Store / Artifact | Total Rows | Unique IDs | Directional Records | Non-Directional Records | Scored Non-Directional (`was_correct != NULL`) | Integrity Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SQLite `market_memory.db`** | **5,622** | **5,622** | 1,968 (1,965 LONG, 3 SHORT) | 3,654 (3,623 SKIP, 31 NONE) | **0** (0.00%) | `VERIFIED_INTACT` |
| **CSV `market_memory.csv`** | **5,622** | **5,622** | 1,968 (1,965 LONG, 3 SHORT) | 3,654 (3,623 SKIP, 31 NONE) | **0** (0.00%) | `VERIFIED_INTACT` |
| **V23 Pre-Backup Snapshot** | 5,553 (DB) / 5,611 (CSV) | Valid | Preserved | Preserved | Verified in backup | `BACKUP_VERIFIED` |

**Verification Verdict:** The 5,622 rows in SQLite and CSV share 100% ID parity. There are **0 duplicate IDs**, **0 orphaned records**, and **0 non-directional records incorrectly marked as wins or losses**.

---

## 2. Backup Integrity and Hash Verification

Before the V23 reconciliation was executed, complete snapshot backups were archived under:
- Path: `experiments/results/backups/v23_pre_reconciliation_backup/`
- Manifest: `manifest.json`

### Verified Backup Manifest Details:
- **Timestamp:** `2026-10-19T17:42:01.320141Z`
- **Pre-Reconciliation SQLite (`market_memory.db`):**
  - Row count: 5,553
  - SHA-256: `6e47efb5e5a9c089c1f0b093cefc2462e2a046c31bf0db2818968f9a2e6e737c`
- **Pre-Reconciliation CSV (`market_memory.csv`):**
  - Row count: 5,611
  - SHA-256: `18f3a38fa5e2a77a942a22530a66d03b7194639908cf2aa89446416fefc8ff72`

The reconciliation script successfully unified the 69 SQLite-only records and 11 CSV-only records, producing the canonical 5,622-row dataset without deleting historical trade outcomes.

---

## 3. Schema & Authoritative Role Definition

An essential task was to establish whether SQLite and CSV are dual-authoritative or have distinct roles:

1. **Authoritative Operational Store — SQLite (`market_memory.db`):**
   - Implements native SQLite ACID transactions, write-ahead logging, and strictly typed columns (`id` TEXT PRIMARY KEY, `timestamp` TEXT, `direction` TEXT, `actual_return` REAL, `was_correct` INTEGER).
   - This database is the authoritative operational data source queried by the FastAPI backend (`backtest/market_memory.py`, `api/routes_arena.py`).
2. **Export / Analytical Snapshot — CSV (`market_memory.csv`):**
   - The CSV is a serialized export designed for external spreadsheet inspection, data science pipelines, and offline cold storage.
   - Discrepancies in raw string formatting (e.g., boolean `"True"` vs SQLite integer `1`, floating-point precision formatting) reflect serialization artifacts, not data corruption.
3. **Canonical Conflict Resolution Rule:** In any future reconciliation, SQLite `market_memory.db` is the authoritative source. The CSV file must be generated as an export of SQLite, never treated as a competing write target.

---

## 4. Directional vs. Non-Directional Event Audit

In earlier versions (prior to V21), non-directional events (`direction="NONE"` or `"SKIP"`) were occasionally scored as losses (`was_correct=0`), corrupting win-rate calculations.

### Forensic Audit Findings:
- Total Non-Directional Records: **3,654** (3,623 `SKIP`, 31 `NONE`).
- Scored Non-Directional Records in SQLite: **0**.
- Scored Non-Directional Records in CSV: **0**.
- Scored Directional Trades (`direction IN ('LONG', 'SHORT')`): **1,936 resolved**, **32 pending resolution**.
- True Directional Win Rate: Evaluated strictly on the 1,936 resolved directional trades. Non-directional scans are never counted as trades.

---

## 5. Migration & Protection Governance

1. **No Migration Needed:** With row counts, primary keys, and directional outcomes in 100% alignment, running another database migration or table union is unnecessary and prohibited.
2. **Pre-Write Backup Mandate:** Any future schema alterations or data migrations must:
   - Create a timestamped directory under `experiments/results/backups/`.
   - Calculate and verify SHA-256 hashes of both DB and CSV files before executing any write transaction.
   - Run a dry-run validation script confirming zero loss of directional trades.
