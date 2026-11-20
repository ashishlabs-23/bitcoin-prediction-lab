# V32.80 — Test and Governance Report (Workstream 7)
**Milestone:** BTCognitive V32.80 — Research Integrity & Reproducibility Audit  
**Generated:** 2026-10-30T17:15:00Z  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Executive Summary

In accordance with the Manager's ruling for V32.80, this report audits the regression test suites, operational health gates, and governance constraints. 

Crucially, the test suites are formally bifurcated into:
1. **Deterministic Governance and Regression Suites** (57 tests across 8 test modules) — **100% PASS (57/57)**.
2. **Operational Data-Freshness Tests** (9 tests across 2 modules) — **FAIL (9 failures)** due to live candle age (>3.8 hours vs. 3.0-hour operational staleness threshold).

The 9 operational failures are confirmed to be a pre-existing operational staleness artifact resulting from the idle data collector under `OFFLINE_RESEARCH_ONLY` invariants, not code regression. The 3.0-hour freshness threshold has **not** been relaxed or weakened.

---

## 2. Test Suite Stratification

### 2.1 Deterministic Governance & Regression Baseline (57 Tests)

The authoritative 8-file governance suite executes cleanly:
- `tests/test_v32_47_analyse_selection_and_anomaly_monitor.py`
- `tests/test_v32_48_integrated_analyse_and_tournament.py`
- `tests/test_longitudinal_api.py`
- `tests/test_longitudinal_dashboard.py`
- `tests/test_longitudinal_status.py`
- `tests/test_sqlite_reliability_integration.py`
- `tests/test_experiment_integrity_v4.py`
- `tests/test_stage8_data_experiments.py`

**Result:** **57 passed, 16 warnings, 0 failures**.
- File-backed SQLite reliability and write-lock isolation: PASS
- Longitudinal API and dashboard telemetry: PASS
- Experiment integrity and deterministic seed guards: PASS
- Selection and tournament abstain logic: PASS

### 2.2 Operational Data-Freshness Tests (9 Failures)

- `tests/test_scenario_planner_and_inference_v6.py` (5 failures)
- `tests/test_scenario_freshness_and_contract_v7.py` (4 failures)

**Root Cause:**
Both files test live data ingestion freshness against real parquet files on disk (`data/raw/ohlcv.parquet`). The latest closed candle timestamp is `2026-10-30 13:00:00+00:00`. At evaluation time, elapsed wall-clock time is >3.8 hours (>13,600s), which violates the strict 3.0-hour (`10,800s`) staleness assertion:
```python
assert result["status"] == "SUCCESS", f"Failed for horizon {hz}: {result.get('rejection_narrative')}"
# AssertionError: Market data timestamp (2026-10-30T13:00:00+00:00) is 13418.0s old, exceeding conservative maximum allowable staleness threshold of 10800.0s (3.0 hours).
```

Per Manager instruction, the 3-hour requirement is **not** weakened. These tests serve as operational freshness monitors when the ingestion runner is live; under offline research freeze, staleness is expected.

---

## 3. Governance Invariant Audit

| Governance Boundary | Mandated Status | Actual Verified Status | Compliance |
|---|---|---|---|
| **Network Isolation** | Zero outbound requests | Confirmed zero network calls | ✅ FULL COMPLIANCE |
| **Model Authorization** | `OFFLINE_RESEARCH_ONLY` | Unchanged across all registries | ✅ FULL COMPLIANCE |
| **Analysis Gate** | `ABSTAIN` (lines 1162–1204) | Untouched; defaults to abstain | ✅ FULL COMPLIANCE |
| **Trading Execution** | `DISABLED` | No order routing / broker code | ✅ FULL COMPLIANCE |
| **Prospective Ledger** | Frozen at 7/100 blocks | 7 blocks preserved; PID 31676 stopped | ✅ FULL COMPLIANCE |
| **Prospective Runner Lock** | Do not restart | `data/.prospective_shadow_runner.lock` untouched | ✅ FULL COMPLIANCE |
| **Protected Datasets** | Checkpoints unmodified | Checkpoint 42,233 SHA-256 MATCH | ✅ FULL COMPLIANCE |
| **Git Working Tree** | No commits/pushes/branching | `main` branch, working tree preserved | ✅ FULL COMPLIANCE |
| **Cloud AI / External Adapters** | Disabled / No API calls | No Gemini or external calls executed | ✅ FULL COMPLIANCE |

---

## 4. Protected Dataset Hashes Verification

Verified via `v32_80_protected_hash_verification.json`:
- `data/raw/ohlcv_checkpoint_42233_bars.parquet`: `f5c15cb11b9d51cf0077c8f8052086382deb1d8577749cbab8d0134842c7a94f` (MATCH)
- `data/raw/ohlcv_version_42326_bars.parquet`: `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057` (MATCH)
- `data/raw/binance_funding_2022_2026.parquet`: `e90282de4f78ebde...` (RECORDED)
- `data/processed/multi_regime_features.parquet`: `e37fcc1a896e5a8a...` (SYNTHETIC_DATA_NOT_VALID RECORDED)
- `data/prospective_entry_ledger.jsonl`: `91c3aed984002f61...` (RECORDED)
- `data/prospective_entry_ledger_v2.jsonl`: `e6e33e3c7beb4c25...` (RECORDED)
- `data/prospective_shadow_v1.jsonl`: `e3b0c44298fc1c14...` (RECORDED)

---

## 5. Summary Determination

The test suite health matches the exact dual-track reality outlined by the Manager:
- 57 deterministic governance/regression tests pass without regression.
- 9 operational freshness failures remain isolated to the data collector idle duration.
- All core governance boundaries remain rigorously intact.

