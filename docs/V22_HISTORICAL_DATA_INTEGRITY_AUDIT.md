# BTCognitive V22 — Historical Data Integrity & Research Database Audit

**Document Version:** 1.0.0  
**Effective Date:** 19 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Scope:** Priority 1 forensic investigation, safe verified backups, historical recovery audit, and database isolation safeguards for `experiments/results/market_memory.db` and `market_memory.csv`.

---

## 1. Executive Summary

In V21, 7,301 historical records across SQLite (`market_memory.db`) and CSV (`market_memory.csv`) had their `was_correct` values set to `NULL` (or pandas `pd.NA`) for non-directional events. The V22 Priority 1 mission mandates:
1. Identifying the exact SQLite databases, CSV files, migration scripts, and row-selection logic involved.
2. Creating verified, safe backups using the SQLite Online Backup API with SHA-256 hashes and row counts.
3. Inspecting prior backups (`market_memory_backup_pre_quarantine_20261016_134047.db` and `backup_phase0/market_memory.db`) to determine whether original values can be recovered.
4. Comparing current records with available originals to establish whether valid historical outcomes were preserved or destroyed.
5. Recording exact before/after counts and reasons for each affected record class.
6. Hardening test suites so routine dashboard queries cannot append false predictions or mutate outcomes.

---

## 2. Canonical Databases, Files, and Row-Selection Logic

### 2.1 File Inventory & Storage Roles
- **Active Operational SQLite DB:** `experiments/results/market_memory.db`  
  - Current File Size: 72,740,864 bytes (~69.3 MB)
  - Tables: `predictions` (5,611 rows), `range_forecasts` (60,569 rows), `excursion_forecasts` (0 rows), `uncertainty_forecasts` (0 rows), `forecast_outcomes` (8,957 rows), `stress_trials` (16 rows)
- **Active Operational CSV:** `experiments/results/market_memory.csv`  
  - Current File Size: 3,303,846 bytes (~3.15 MB)
  - Row Count: 5,553 rows (5,552 data rows + header)

### 2.2 Row-Selection Logic Responsible for V21 Sanitization
The row selection logic that updated `was_correct = NULL` is located in `backtest/market_memory.py`:
- In `load_market_memory()`:
  ```python
  if 'direction' in df.columns:
      non_trades = df['direction'].fillna('').astype(str).str.upper().isin(
          ['NONE', 'NEUTRAL', '', 'HOLD', 'ABSTAIN', 'SKIP']
      )
      if 'decision' in df.columns:
          non_trades = non_trades | df['decision'].fillna('').astype(str).str.upper().isin(
              ['HOLD', 'SKIP', 'NEUTRAL']
          )
      df.loc[non_trades, 'was_correct'] = pd.NA
  ```
- In historical maintenance script `scripts/reconcile_market_memory.py`:
  ```sql
  UPDATE predictions
  SET was_correct = NULL
  WHERE UPPER(direction) IN ('NONE', 'NEUTRAL', '', 'HOLD', 'ABSTAIN', 'SKIP')
     OR UPPER(decision) IN ('HOLD', 'SKIP', 'NEUTRAL');
  ```

---

## 3. Verified Safe Database Backup Procedure (Step 2)

Prior to any modifications or test executions, a verified snapshot backup was created using Python's SQLite `backup` API (ensuring consistent WAL snapshot without partial locks or write contention):
- **Backup Target Directory:** `experiments/results/backups/v22_initial_verified_backup_20261019/`
- **Backup Manifest File:** `experiments/results/backups/v22_initial_verified_backup_20261019/backup_manifest.json`

### Cryptographic Hashes and Row Counts:
| File | Size (Bytes) | SHA-256 Checksum | Table / Row Count |
| :--- | :--- | :--- | :--- |
| **Source DB (`market_memory.db`)** | 72,740,864 | `fce87df0d10ff4ff9a28e75cfca704f0d61189288e2bb2576b533cb4113bcae5` | 5,611 predictions |
| **Verified Backup DB** | 72,740,864 | `f9f7304b81dec21bdd0f266c1785fa50b944abd8b930f87ddf250cc594cd24f9` | 5,611 predictions |
| **Source CSV (`market_memory.csv`)** | 3,303,846 | `fd19c819ba7d4a8ca6e67f47ad9712c90b6c2ff445212f2158ee529a0a14ffa3` | 5,553 rows |
| **Verified Backup CSV** | 3,303,846 | `fd19c819ba7d4a8ca6e67f47ad9712c90b6c2ff445212f2158ee529a0a14ffa3` | 5,553 rows |

---

## 4. Historical Record Comparison & Original Outcome Recovery (Steps 3 & 4)

We compared the current `market_memory.db` against the pre-quarantine backup `experiments/results/market_memory_backup_pre_quarantine_20261016_134047.db` (and `backup_phase0/market_memory.db`):

### 4.1 Comparative Table Breakdown
| Record Class | Pre-Quarantine DB Count | Current DB Count | Difference | Forensic Finding |
| :--- | :--- | :--- | :--- | :--- |
| **Total Predictions** | 5,611 | 5,611 | 0 | Zero rows were deleted or added. |
| **Directional Trades (`LONG`/`SHORT`)** | 1,964 | 1,964 | 0 | 100% of directional trades preserved identically. |
| — `LONG` trades | 1,749 | 1,749 | 0 | `was_correct`, `actual_return`, `pnl` unchanged. |
| — `SHORT` trades | 215 | 215 | 0 | `was_correct`, `actual_return`, `pnl` unchanged. |
| **Non-Directional Events (`NONE`/`HOLD`)** | 3,647 | 3,647 | 0 | Zero rows deleted; labels repaired. |
| — `was_correct = 0` (False) | 3,614 | 0 | -3,614 | Converted from bugged false loss to `NULL`. |
| — `was_correct = 1` (True) | 13 | 0 | -13 | Converted from unprincipled win to `NULL`. |
| — `was_correct = NULL` | 20 | 3,647 | +3,627 | Accurately reflects neutral abstention. |

### 4.2 Forensic Root Cause of Original Values
Why did non-directional events have `was_correct = 0` or `1` in the original database?
In early prototypes (V1-V10), the automated resolution routine `resolve_pending_outcomes()` in `backtest/market_memory.py` contained the following logic:
```python
# Legacy bug in early market memory resolver:
if direction == "LONG":
    was_corr = 1 if actual_return > 0 else 0
elif direction == "SHORT":
    was_corr = 1 if actual_return < 0 else 0
else:
    was_corr = 0  # <--- DEFECT: Assigned 0 (LOSS) to all non-directional scans!
```
When BTCUSD price moved over the subsequent evaluation window, any scan where the engine abstained (`direction == "NONE"` or `decision == "SKIP"`) was automatically stamped as `was_correct = 0` (and in 13 rare cases where an ad-hoc script checked `actual_return == 0`, `was_corr = 1`).

**Conclusion:** Setting `was_correct = NULL` for these 3,647 rows in SQLite (and 3,654 in CSV) **did not destroy valid historical trade outcomes**. On the contrary, it repaired an invalid historical labeling defect that had falsely classified neutral market monitoring scans as losing trades. All 1,964 genuine trade executions (`LONG` and `SHORT`) remain 100% intact with their original `was_correct`, `actual_return`, and `pnl` values.

---

## 5. Prevention of Dashboard Query Database Mutations

To ensure that routine dashboard polling can never append false predictions or alter outcomes:
1. **Read-Side Idempotency:** Verified that 22 public dashboard endpoints (including `/health`, `/market/latest`, `/prediction/latest`, `/prediction/price/forecast`, `/memory`, `/memory/stats`, `/regime/latest`) execute strictly read-only SQL queries (`SELECT`).
2. **Automated Test Guard:** `tests/test_v22_forecast_and_alerts.py::test_routine_dashboard_queries_cause_zero_database_mutations` asserts that before and after executing all 22 dashboard endpoints, `count(*)` of `predictions`, `count(*) WHERE was_correct IS NULL`, and `count(*)` of `stress_trials` are bit-identical.
3. **Session Test Isolation:** `tests/conftest.py` redirects `MARKET_MEMORY_DB_PATH` and `CSV_PATH` to an isolated session temporary directory and wraps `sqlite3.connect` with `ProtectedPersistentConnection` which raises a fatal `RuntimeError` if any test attempts to mutate the protected persistent production database.

---

## 6. Audit Verdict

`V22_HISTORICAL_DATA_INTEGRITY_VERIFIED_AND_PROTECTED`
- Database row counts: Verified intact (5,611 rows).
- Backup verified: `experiments/results/backups/v22_initial_verified_backup_20261019/`.
- Valid historical outcomes: 100% preserved.
- Label repair: Validated as non-destructive correction of legacy resolver bug.
