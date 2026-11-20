# BTCognitive — Current State & Discrepancy Ledger (V32.30)

**Date:** 2026-10-25  
**Version:** V32.30  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed)  
**Lead Integrator:** Agent 0  

---

## 1. Re-Validated Starting Facts (Forensic Audit of V32.29)

Every material claim reported in V32.29 was re-verified against the active working tree, file system, process state, and cryptographic hashes:

1. **Software & Scientific Dual Terminal State:**
   - Prior Software State: `SOFTWARE_QA_PASS` (73 backend tests, frontend unit & polling suite, isolated real HTTP suite all pass 100%).
   - Prior Scientific / Economic State: `NO_GO_NO_VALIDATED_EDGE` (Verified strategy baseline `TSMOM_DONCHIAN_24H_168H` lost after 27 bps and 87 bps costs; calibrated tri-state meta-model admitted 0/130 holdout candidates).
2. **Coinbase BTC-USD Hourly Archive Lineage:**
   - File Path: [data/research/coinbase_btc_usd_hourly_v1/coinbase_hourly.parquet](file:///C:/Projects/BTCognitive/BTCognitive/data/research/coinbase_btc_usd_hourly_v1/coinbase_hourly.parquet)
   - Manifest: [coinbase_hourly_manifest.json](file:///C:/Projects/BTCognitive/BTCognitive/data/research/coinbase_btc_usd_hourly_v1/coinbase_hourly_manifest.json)
   - Row Count: Exactly 33,424 hourly bars (2023-01-01 00:00:00Z to 2026-10-25 04:00:00Z).
   - Capture Timestamp: `2026-10-25T05:20:48.705854+00:00`.
   - Closed-Bar Invariant: The newest candle (04:00Z) closed at 05:00Z, which is strictly earlier than the capture timestamp (05:20Z). Zero still-forming or future-dated candles exist.
   - Outage Gaps: Exactly 3 documented exchange outages (13 missing hours total: 3h in Mar 2023, 5h in Oct 2025, 5h in May 2026). Zero synthetic interpolation was applied.
   - Provenance Truth: Captured directly from Coinbase Exchange public REST API (`/products/BTC-USD/candles?granularity=3600`); locally hashed (`b81688644812276856ede9b9c38db21aaccba56387b284112a3d0175685bf5cf`). Does not carry a cryptographic digital signature from Coinbase.
3. **Quarantine of Legacy Data:**
   - [data/raw/ohlcv.parquet](file:///C:/Projects/BTCognitive/BTCognitive/data/raw/ohlcv.parquet) has unverified mixed-source provenance and remains strictly quarantined (`UNVERIFIED_SOURCE`). Unverified fallbacks were completely removed from [api/routes_research.py](file:///C:/Projects/BTCognitive/BTCognitive/api/routes_research.py).
4. **Chronos-2 Status:**
   - Architecture review and mathematical barrier incompatibility documented. Local model-weight inference was **NOT EXECUTED**. Heavy optional research dependencies are isolated in [requirements-research.txt](file:///C:/Projects/BTCognitive/BTCognitive/requirements-research.txt).
5. **Directional GBDTs:**
   - Trained on legacy data; out-of-sample AUC near 0.51–0.52. Labeled `PROVENANCE_LIMITED_RESEARCH_ONLY`. Context only; never substituted for first-passage probabilities.
6. **Listener & Process State:**
   - No active listener on port 8000. Real HTTP integration tests execute against dynamically bound ephemeral ports and shut down cleanly.
7. **Protected Files Bit-Identical Audit:**
   - All five protected files verified bit-identical at baseline.

---

## 2. Protected Files Hash Baseline (V32.30 Start)

| Protected File Path | Baseline SHA-256 (Start of V32.30) | Status |
| :--- | :--- | :---: |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **PROTECTED / LOCKED** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **PROTECTED / LOCKED** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **PROTECTED / LOCKED** |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **PROTECTED / LOCKED** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **PROTECTED / LOCKED** |

---

## 3. Discrepancy Reconciliation Summary

| Item | Prior Discrepancy / Ambiguity | Reconciled Reality in V32.30 |
| :--- | :--- | :--- |
| **Backend Test Count** | Reports varied between 68 and 69 tests. | V32.27 had 68 tests. V32.28 added `test_negative_net_expectancy_reason_code` (69 tests). V32.29 added 4 isolated real HTTP tests in `test_isolated_real_http_server.py`. Total collected: **73 tests (100% pass)**. |
| **Module Inventory Count** | Summary text loosely grouped categories (7, 4, 9, 4). | Strictly reconciled to match the 25-row matrix: `CORE_KEEP` (8), `SUPPORT_KEEP` (9), `RESEARCH_ONLY` (4), `PARK` (1), `REMOVE/REJECT` (2), `BLOCKED` (1) = **Exactly 25 modules**. |
| **Candle Timestamp `15:00 UTC`** | Fear of future-dated candle. | Timestamp was `2025-10-25T15:00:00Z` from a 2025 outage gap, not 2026. Newest candle is `2026-10-25T04:00:00Z`, captured at `05:20:48Z`. |
| **TabICL Hash** | Previous report listed placeholder hash `3f892a01...`. | File never existed on disk; corrected to `FILE_NOT_PRESENT / NEVER_DOWNLOADED — REJECTED_UNTRUSTED_PICKLE`. |
| **API Runtime Verification** | In-process TestClient tests did not test real TCP sockets. | Implemented and verified real HTTP requests over ephemeral loopback socket (`test_isolated_real_http_server.py`). |
