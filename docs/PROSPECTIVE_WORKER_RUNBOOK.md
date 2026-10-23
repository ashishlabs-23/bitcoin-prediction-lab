# BTCognitive — Prospective Worker Operations & Runbook

**Version:** 1.1.0 (V7 Audited)  
**Effective Date:** 17 October 2026  
**Component:** `engine/prospective_worker.py` / `scripts/run_prospective_worker.ps1`  
**Ledger Path:** `data/prospective_forecast_ledger.jsonl`  
**Telemetry Path:** `data/prospective_worker_status.json`  

---

## 1. Operational Overview & Governance Boundaries

The Prospective Evidence Worker automates the collection of confirmatory out-of-sample evidence for BTCognitive:
1. **Live Closed-Candle Synchronization:** Fetches recent hourly bars from Coinbase Exchange API (`BTC-USD`, granularity 3600), drops the forming hour, validates OHLC consistency, and atomically appends new bars to `data/raw/ohlcv.parquet`.
2. **Deterministic Outcome Resolution:** Checks all `PENDING` records in `data/prospective_forecast_ledger.jsonl`. When $t_{\text{now}} \ge t_{\text{maturity}}$, computes the forward realized variance from closed candles. If candles are temporarily delayed, applies a 6-hour settlement grace period before logging an exclusion.
3. **Dual-Target Prospective Issuance:** Strictly at the latest closed bar cutoff $t$, generates matched predictions:
   - **Target 1 (24H):** `HAR-QLIKE-24H-v1.0` vs. Persistence, Rolling 30D, and OLS-HAR on `rv24h_var_ann`.
   - **Target 2 (168H):** `HAR-RS-DOW-v1.0` vs. Persistence and Rolling 30D on `rv7d_var_ann`.
4. **Idempotency Invariant:** Duplicate issue attempts for the same target and issue timestamp are automatically detected and rejected without mutating the ledger.
5. **Strict Non-Execution:** All predictions serve market risk intelligence and excursion analysis. Zero live capital, zero exchange order placement, zero automated promotion.

---

## 2. V7 Ledger Audit & Classification Breakdown

An independent audit of `data/prospective_forecast_ledger.jsonl` as of 17 October 2026 establishes:
- **Total Logged Records:** 9 records.
- **Historical Seed Record (Excluded from Confirmatory Gate):** 1 record (`prospective-seed-001`, issued 2026-08-31 for bootstrapping).
- **Genuine Prospective Records:** 8 records (4 for 24h horizon, 4 for 168h horizon).
- **Resolution State:**
  - `rv24h_var_ann` (24h horizon): 5 total records (1 seed + 4 prospective), **all 5 are RESOLVED**.
  - `rv7d_var_ann` (168h horizon): 4 total prospective records, **all 4 remain PENDING** (scheduled maturities 2026-10-22 to 2026-10-23).
- **Clean Non-Overlapping Blocks:**
  - Strictly non-overlapping 24h blocks: **1 block** (`b1203745-8d96-429c-973e-f35d1a49b843`, issued 2026-10-15 17:00 UTC, matured 2026-10-16 17:00 UTC).
  - Subsequent 24h issuances on 2026-10-16 overlap with this initial window.
- **Confirmatory Hurdle Progress:** `1 / 100` strictly non-overlapping clean blocks (or `5 / 100` raw resolved blocks).
- **Governed Status:** `COLLECTING`.
- **Confirmatory Gate:** `NOT_SATISFIED` (`is_sufficient_for_confirmatory = false`). Live trading remains permanently `DISABLED`.

---

## 3. Operational State Truthfulness

The system distinguishes three execution modes:
1. **Manual / CLI Dry-Run (`STANDALONE_CLI_SCHEDULED`):**
   - Single cycle executed on-demand.
   - Status file records `is_autonomous_process_running: false`.
2. **Local Autonomous Daemon (`CONTINUOUS_DAEMON_RUNNING`):**
   - Process running in background loop (`--daemon --interval 3600`).
   - Status file records `is_autonomous_process_running: true`.
3. **OS-Level Scheduled Task (`SYSTEM_SCHEDULED`):**
   - **Current Status: NOT CONFIGURED.**
   - In accordance with non-negotiable governance, no persistent Windows Task Scheduler job is registered without explicit user sign-off.
   - `schtasks /Query /TN "BTCognitiveProspectiveWorker"` confirms: `ERROR: The system cannot find the file specified`.

---

## 4. Tested Execution & Dry-Run Procedures

### Procedure 1: Offline Dry-Run (No Network Access)
Tests deterministic resolution and duplicate-skip logic against local parquet data:
```powershell
.\.venv_win\Scripts\python.exe -m engine.prospective_worker --once --no-sync
```

### Procedure 2: Online Single Cycle with Live Candle Sync
Fetches new closed candles from Coinbase API, resolves matured outcomes, and issues prospective forecasts:
```powershell
.\.venv_win\Scripts\python.exe -m engine.prospective_worker --once --sync-live
```
Or via PowerShell runner:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_prospective_worker.ps1 -SyncLive
```

### Procedure 3: Status Telemetry Inspection
```powershell
.\.venv_win\Scripts\python.exe -m engine.prospective_worker --status
```
Or inspect `data/prospective_worker_status.json` directly.

### Procedure 4: Optional Production Windows Scheduler Setup (Reference Only)
If explicitly approved by system operator:
```cmd
schtasks /Create /SC HOURLY /TN "BTCognitiveProspectiveWorker" /TR "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\Projects\BTCognitive\BTCognitive\scripts\run_prospective_worker.ps1 -SyncLive" /ST 00:05
```
To verify:
```cmd
schtasks /Query /TN "BTCognitiveProspectiveWorker" /FO LIST /V
```
To remove:
```cmd
schtasks /Delete /TN "BTCognitiveProspectiveWorker" /F
```

---

## 5. Failure Recovery & Concurrency Invariants

- **Single-Instance Locking:** Enforced via `data/.prospective_worker.lock` containing current PID. Competing processes exit immediately with `LOCKED_ANOTHER_INSTANCE_RUNNING` without modifying the ledger.
- **Atomic Append:** The ledger (`prospective_forecast_ledger.jsonl`) is updated using append-only writes. Completed lines are immutable; resolutions append a state-transition event or rewrite in atomic temp-replace format.
- **Crash Recovery:** If a crash occurs during a cycle, the next invocation detects existing forecasts via hash/timestamp and resumes from the latest valid state.
