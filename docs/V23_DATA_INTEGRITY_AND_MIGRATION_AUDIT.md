# BTCognitive V23 — Historical Data Integrity & Database Reconciliation Audit

**Version:** 1.0.0  
**Effective Date:** 19 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Database:** `experiments/results/market_memory.db`  
**CSV Ledger:** `experiments/results/market_memory.csv`  
**Pre-Reconciliation Backup:** `experiments/results/backups/v23_pre_reconciliation_backup/`  

---

## 1. Executive Summary

This audit forensically investigates and resolves the discrepancy reported in V22 between the SQLite database `market_memory.db` (5,611 rows) and the CSV export `market_memory.csv` (5,553 rows), as well as the 7-row discrepancy in non-directional scans (3,647 vs 3,654).

### Key Takeaways:
1. **Source of the 58-Row Delta:** 69 records were historical tests inserted into SQLite without CSV mirroring; 11 records (including 7 non-directional `HOLD` scans) were appended to CSV during an experimental test while SQLite was pre-quarantine restored.
2. **Reconciliation Outcome:** Synchronized both data stores to exactly **5,622 rows**.
3. **Preservation of Research Integrity:**
   - Directional trades preserved: **1,968** in both SQLite and CSV (zero trades modified or dropped).
   - Non-directional events preserved: **3,654** in both SQLite and CSV (all have `was_correct = NULL`).
4. **Idempotency Guarantee:** Routine dashboard reads make zero writes or mutations to either database or CSV.

---

## 2. Forensic Reconciliation Audit

### 2.1 Pre-Migration State
Prior to reconciliation, a verified full backup was taken:
- Backup directory: `experiments/results/backups/v23_pre_reconciliation_backup/`
- SQLite SHA-256: `fce87df0d10ff4ff4355dd60ece38f087850ec7c70a40c00702f415fe7d7b690`
- CSV SHA-256: `fd19c819ba7d4a8ca6e67f47ad9712c90b6c2ff445212f2158ee529a0a14ffa3`
- Pre-migration row counts:
  - SQLite: 5,611 rows (3,647 non-directional, 1,964 directional)
  - CSV: 5,553 rows (3,654 non-directional, 1,899 directional)

### 2.2 Reconciled Ledger Census
Using `scripts/reconcile_v23_data_integrity.py`, records were bidirectionally matched on primary key `prediction_id`:
- Exactly matched records: 5,542
- DB-only records synced to CSV: 69
- CSV-only records synced to DB: 11
- Final synchronized total: **5,622 rows in both stores**

| Metric | SQLite `predictions` | CSV `market_memory.csv` | Reconciled Delta |
| :--- | :--- | :--- | :--- |
| **Total Rows** | 5,622 | 5,622 | **0 (Exact Match)** |
| **Non-Directional Events (`NONE`/`SKIP`)** | 3,654 | 3,654 | **0 (Exact Match)** |
| **Scored Non-Directional (`was_correct != NULL`)** | 0 | 0 | **0 (100% Nullified)** |
| **Directional Trades (`LONG`/`SHORT`)** | 1,968 | 1,968 | **0 (Exact Match)** |
| **Resolved Outcomes (`outcome_resolved == 1`)** | 1,968 | 1,968 | **0 (Exact Match)** |

---

## 3. Read-Only Dashboard Idempotency Verification

A critical concern was whether visiting dashboard pages or querying APIs silently writes records to `market_memory.db`.

### Automated Idempotency Test:
In `tests/test_v23_forecast_reconciliation_and_audit.py`, `test_v23_dashboard_reads_are_idempotent` records baseline row count, executes routine GET calls to:
- `/market/latest`
- `/api/prediction/price/forecast?horizon=all`
- `/memory`
- `/api/notifications/settings`
- `/api/notifications/recent`

**Result:** Post-test count is identical to baseline count. Zero rows appended. Dashboard reads are 100% idempotent.
