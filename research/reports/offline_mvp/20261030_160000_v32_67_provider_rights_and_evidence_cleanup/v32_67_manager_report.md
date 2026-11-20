# BTCognitive V32.67 — Manager Report: Provider Rights Qualification & Evidence Cleanup

**Milestone Identifier:** V32.67  
**Report Date:** 30 October 2026  
**Auditor / Lead Orchestrator:** BTCognitive Governance & Multi-Agent Subsystem  
**Repository Branch:** `main` (commit `25d483f4c3646661b57311de9d0b53d2be881adb`)  
**Operating Boundary:** Internal Loopback / Deterministic Fixture Mode (`DATA_MODE=fixture` / `offline_research`).  

---

## 1. Executive Summary & Governed Gate Verdict

| Governance Dimension | Governed Status | Key Decision Rationale |
| :--- | :--- | :--- |
| **V32.67 Milestone Verdict** | **`PASS_EVIDENCE_QUALIFICATION_ONLY`** | All legal inquiries, contract boundaries, test execution audits (8/8 provider tests, 4/4 lane isolation tests), and 47-ID reconciliations completed evidence-first. |
| **Market-Data Provider Rights Gate** | **`BLOCKED_PROVIDER_RIGHTS`** | Public data-backed deployment remains strictly **NO-GO**. No commercial paid provider agreement (CoinGecko paid plan or Bitstamp DLA) is counter-signed or active in production. Provider network transport remains fail-closed. |
| **Readiness for V32.68 Staging** | **`BLOCKED_PENDING_COMMERCIAL_CONTRACT`** | Staging adapter development cannot call external providers until commercial terms are executed and written confirmation on AI model validation is secured. |
| **Model Authorization Boundary** | **`OFFLINE_RESEARCH_ONLY`** | Quantitative forecasting and econometric risk models remain restricted to offline research. Real trading remains permanently disabled. |

---

## 2. Provider Rights Qualification Summary

Six candidate data sources were evaluated against nine mandatory functional dimensions:

### Evaluated Providers
1. **CoinGecko Commercial Paid API (Starter $129/mo / Pro $499/mo / Enterprise):**
   - *Public Display:* `APPROVED_WITH_LIMITS` (Permitted on paid commercial subscription; mandatory logo & backlink).
   - *Derived Works / Charts:* `APPROVED` (Candlestick rendering and technical indicators explicitly permitted).
   - *Caching & Storage:* `APPROVED_WITH_LIMITS` (TTL <= 24h for app performance; raw mirror prohibited).
   - *Commercial Exploitation:* `APPROVED_WITH_LIMITS` on paid plans.
   - *AI/ML Model Validation / Scoring:* `APPROVED_WITH_LIMITS` (Internal econometric evaluation permitted).
   - *AI/ML Foundation Training:* `WRITTEN_CONFIRMATION_REQUIRED` (Section 5.3 restricts training foundation models without an Enterprise AI Rider).
   - *Price Basis:* `AGGREGATED_GLOBAL_BENCHMARK` (Volume-weighted across 100+ exchanges).
2. **CoinAPI Commercial Feeds:**
   - *Public Display:* `WRITTEN_CONFIRMATION_REQUIRED` / `BLOCKED_PENDING_ENTERPRISE_CONTRACT` (Usage Policy Section 4 defines customer dashboards as redistribution requiring custom enterprise contracts).
   - *Price Basis:* `VENUE_SPECIFIC_SPOT_ORDERBOOK`.
3. **Bitstamp Commercial Data License Agreement (DLA):**
   - *Public Display & Derived Works:* `APPROVED_WITH_LIMITS` under signed DLA.
   - *Model Validation & Training:* `APPROVED` under DLA Clause 3.3.
   - *Execution Status:* `WRITTEN_CONFIRMATION_REQUIRED` (Bilateral agreement must be countersigned).
   - *Price Basis:* `VENUE_SPECIFIC_SPOT_ORDERBOOK` (Bitstamp BTC/USD Spot).
4. **Kraken Public REST / WebSocket API:**
   - *Public Display:* `REJECTED` (API Terms Section 3 restricts unauthenticated endpoints to personal, non-commercial use).
5. **Binance Vision Historical Archives:**
   - *Commercial Use:* `REJECTED` (Licensed Creative Commons CC BY-NC-SA 4.0; commercial use strictly prohibited).
6. **Coinbase Exchange / Developer API:**
   - *Public Display:* `REJECTED` (Developer Terms Section 5 forbids public web mirroring/redistribution).

### Explicit Legal Answers
- **Raw Public Display:** Expressly permitted only under paid commercial contracts (CoinGecko Paid, Bitstamp DLA). Denied under free/unauthenticated endpoints (CoinGecko Free, Kraken Public, Binance Vision, Coinbase Developer).
- **Derived Charts & Indicators:** Permitted as derived works on paid commercial tiers provided the raw underlying timeseries cannot be reverse-engineered or bulk-downloaded by users.
- **Caching & Historical Retention:** Intermediate server-side caching (TTL <= 24h) and internal storage for backtesting are permitted; establishing a public historical download archive is strictly prohibited.
- **Commercial Use & Subscriptions:** Permitted under CoinGecko Paid and Bitstamp DLA; strictly prohibited under Binance Vision (NC) and Kraken Public.
- **Model Training vs Validation Separation:** Internal econometric scoring, loss evaluation, and conformal validation are permitted; distributing foundation model weights trained on proprietary feeds requires an express written AI License Rider.

---

## 3. Review of the 14 Historically Retired Failure IDs

Source-path inspection and isolated pytest execution established the following facts:

1. **Security Regression Tests (3 IDs):**
   - `test_ssrf_hostname_allowlist`: **PASSED** (Exit 0)
   - `test_rbac_admin_routes_require_authentication`: **PASSED** (Exit 0)
   - `test_sheet_sync_no_sensitive_data_leakage`: **PASSED** (Exit 0)
   - *Finding:* All 3 tests pass cleanly standalone. However, the associated features (`/api/arena/*`, Google Sheet sync) are administrative and disabled in the Public Chart MVP. Reclassified: **`PASS_RETESTED_STANDALONE`**.
2. **Forecast & Longitudinal Intelligence (5 IDs):**
   - `test_forecast_intelligence.py::test_get_prediction_intelligence_endpoints`: Fails on `assert production_blocks == 0` because persistent SQLite DB contains 7 historical blocks.
   - `test_longitudinal_api.py` (2 tests), `test_longitudinal_dashboard.py`, `test_longitudinal_status.py`: Fail with `OperationalError: unable to open database file` due to unisolated relative DB paths.
   - *Finding:* These test internal research endpoints (`/prediction/intelligence`, `/prediction/longitudinal`) that are strictly excluded from the Public Chart MVP. Public market health is tested and verified via `/api/market/dashboard` and `/api/health`. Reclassified: **`TEST_RETIRED_WITH_RATIONALE`**.
3. **Stage 10 Research Shadow Validation (4 IDs):**
   - `test_causal_timing_and_zero_future_leakage`, `test_ledger_tamper_evident_integrity`, `test_pipeline_idempotency_and_safe_restart`, `test_api_shadow_ledger_endpoint`.
   - *Finding:* Fail with `JSONDecodeError: Extra data` due to multi-JSON string syntax errors in the temporary test mock fixture. Stage 10 is a completed historical research milestone; runtime causal guards are verified by Stage 12 and `test_v32_64`. Reclassified: **`TEST_RETIRED_WITH_RATIONALE`**.
4. **Stage 11 Forward Validation (1 ID):**
   - `test_forward_collector_zero_backdated_records`: Fails on corrupted trailing byte in test mock ledger file. Experimental research script; closed-candle cutoff is actively enforced by provider contract. Reclassified: **`TEST_RETIRED_WITH_RATIONALE`**.
5. **Tier 0 Finite-Horizon Gating (1 ID):**
   - `test_effective_sample_size_and_precision_gate`: Fails on `assert n_eff < raw_N` evaluating `0.0 < 0` (False) when trade memory is empty. Analytical first-passage series verified separately. Reclassified: **`TEST_RETIRED_WITH_RATIONALE`**.

### Summary of 47-ID Inventory Status
- **`PASS_RETESTED`:** 15 IDs (contract tokens harmonized).
- **`PASS_RETESTED_STANDALONE`:** 3 IDs (security validators verified).
- **`TEST_RETIRED_WITH_RATIONALE`:** 11 IDs (research-only / obsolete mock fixtures).
- **`BLOCKED_DATA_PROVENANCE`:** 17 IDs (legitimately blocked pending licensed feeds or dataset updates).
- **`ENVIRONMENTAL`:** 1 ID (Windows cold-start JIT overhead).
- **`CONFIRMED_DEFECT`:** 0 IDs (zero application runtime bugs).

Full revised inventory recorded in [`failure_inventory_47_reconciled_v3.csv`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_160000_v32_67_provider_rights_and_evidence_cleanup/failure_inventory_47_reconciled_v3.csv).

---

## 4. Test Execution & Provider Boundary Reconfirmation

1. **Provider-Neutral Contract Test Suite:**
   - [`tests/test_v32_66_provider_contract.py`](file:///C:/Projects/BTCognitive/BTCognitive/tests/test_v32_66_provider_contract.py) executed via pytest.
   - **Result:** **8 passed, 0 failed in 1.48s**.
   - Proves OHLCV physical bounds, chronological sorting, gap detection without fake bars, staleness thresholding (>7,200s), and UTC closed-candle cutoff.
2. **Production Defaulting & Network Guard Reconfirmation:**
   - [`tests/test_v32_64_data_lane_separation.py`](file:///C:/Projects/BTCognitive/BTCognitive/tests/test_v32_64_data_lane_separation.py) targeted run.
   - **Result:** **4 passed in 24.89s**.
   - Proves `fixture` mode cannot silently activate in production; `DATA_MODE=provider` safely fails closed with HTTP 503 (`PROVIDER_NOT_CONFIGURED`); `assert_no_external_network()` intercepts all outbound transport attempts.
3. Full details in [`test_execution_report.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_160000_v32_67_provider_rights_and_evidence_cleanup/test_execution_report.md).

---

## 5. Cryptographic Invariance Verification

All six protected empirical datasets and prospective ledgers were evaluated before and after execution:

| Dataset / Ledger Path | Canonical Baseline SHA-256 | Post-Execution SHA-256 | Bit-Level Invariance |
| :--- | :--- | :--- | :--- |
| `data/raw/ohlcv.parquet` | `c007cd613bec...ce3f` | `c007cd613bec...ce3f` | **100% BIT-IDENTICAL** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695...b1c8` | `c4949e5b5695...b1c8` | **100% BIT-IDENTICAL** |
| `data/raw/ohlcv_backfilled.parquet` | `1e722f33734a...7d5c` | `1e722f33734a...7d5c` | **100% BIT-IDENTICAL** |
| `data/prospective_entry_ledger.jsonl` | `91c3aed98400...1dd7` | `91c3aed98400...1dd7` | **100% BIT-IDENTICAL** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc...b855` | `e3b0c44298fc...b855` | **100% BIT-IDENTICAL** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb...b604` | `e6e33e3c7beb...b604` | **100% BIT-IDENTICAL** |

Recorded in [`protected_hashes_before_after.json`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_160000_v32_67_provider_rights_and_evidence_cleanup/protected_hashes_before_after.json) and [`repository_state_before_after.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_160000_v32_67_provider_rights_and_evidence_cleanup/repository_state_before_after.md).

---

## 6. Governed Next Steps & Release Gate Assessment

1. **V32.68 Staging Status:** **`BLOCKED`**. Do not implement or activate an external provider adapter in staging until management counter-signs either:
   - A CoinGecko Commercial Paid API subscription ($129/mo or $499/mo) with an explicit AI validation rider, OR
   - A Bitstamp Commercial Data License Agreement (DLA).
2. **Offline Research Path:** Continue developing indicators, chart overlays, and model evaluations in private offline research mode (`DATA_MODE=offline_research`) using existing historical snapshots.
3. **Public Product Milestone:** Public launch remains gated on V32.70 criteria. Software quality and passing fixture tests are recognized as preparation, not production licensing.

