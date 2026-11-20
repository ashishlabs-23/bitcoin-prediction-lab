# V32.80A — Repository Integrity & Working Tree Audit

**Milestone:** BTCognitive V32.80A — Audit Closure Addendum  
**Generated:** 2026-10-30T17:42:00Z  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Git Repository State

| Property | Value / Verification |
|---|---|
| **Active Branch** | `main` |
| **Tracking Upstream** | `origin/main [ahead 1]` |
| **Current HEAD Commit** | `25d483f4c3646661b57311de9d0b53d2be881adb` |
| **Destructive Git Operations** | ZERO (`git checkout .`, `git reset`, `git clean` PROHIBITED) |
| **Branch Creation / Pushes** | ZERO |
| **Modified Working Tree Files** | Preserved exactly as found |
| **Untracked Scratch & Reports** | Confined to `.gitignore` / `research/reports/` directories |

---

## 2. Protected Hash Verification

Verified cryptographically via `v32_80a_protected_hash_verification.json`:

| File | Expected SHA-256 | Actual SHA-256 | Verification Status |
|---|---|---|---|
| `data/raw/ohlcv_checkpoint_42233_bars.parquet` | `f5c15cb11b9d51cf0077c8f8052086382deb1d8577749cbab8d0134842c7a94f` | `f5c15cb11b9d51cf0077c8f8052086382deb1d8577749cbab8d0134842c7a94f` | **MATCH (Pristine)** |
| `data/raw/ohlcv_version_42326_bars.parquet` | `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057` | `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057` | **MATCH (Pristine)** |
| `data/raw/binance_funding_2022_2026.parquet` | N/A | `e90282de4f78ebd...` | **RECORDED (Unmodified)** |
| `data/processed/multi_regime_features.parquet` | N/A | `e37fcc1a896e5a8...` | **RECORDED (Preserved)** |
| `data/prospective_entry_ledger.jsonl` | N/A | `91c3aed984002f6...` | **RECORDED (Frozen)** |
| `data/prospective_entry_ledger_v2.jsonl` | N/A | `e6e33e3c7beb4c2...` | **RECORDED (Frozen)** |
| `data/prospective_shadow_v1.jsonl` | N/A | `e3b0c44298fc1c1...` | **RECORDED (Empty/Frozen)** |

---

## 3. Test Suite Health Breakdown

### 3.1 Deterministic Governance Suite (8 Files, 57 Tests)
**Command:**
```powershell
.venv_win\Scripts\pytest tests/test_v32_47_analyse_selection_and_anomaly_monitor.py tests/test_v32_48_integrated_analyse_and_tournament.py tests/test_longitudinal_api.py tests/test_longitudinal_dashboard.py tests/test_longitudinal_status.py tests/test_sqlite_reliability_integration.py tests/test_experiment_integrity_v4.py tests/test_stage8_data_experiments.py -q
```
**Result:** **57 PASSED, 0 FAILED** (in 14.39s).
- File-backed SQLite write-lock concurrency: PASS
- Longitudinal API and dashboard status telemetry: PASS
- Selection and tournament abstain invariants: PASS
- Model registry authorization gates: PASS

### 3.2 Operational Data-Freshness Tests (2 Files, 9 Tests)
- `tests/test_scenario_planner_and_inference_v6.py` (5 failures)
- `tests/test_scenario_freshness_and_contract_v7.py` (4 failures)
**Result:** **9 FAILURES**.
- **Cause:** Live market data age is >3.8 hours, exceeding the strict 3.0-hour staleness gate.
- **Classification:** Operational data freshness monitor failure under offline collector freeze. Not a code regression. Threshold has not been relaxed.

---

## 4. Governance Constraints Audit

- `OFFLINE_RESEARCH_ONLY`: Active. Zero external network calls.
- `NO_GO_NO_VALIDATED_EDGE`: Active. No trading edges promoted.
- `Analysis ABSTAIN`: Active in `engine/regime_strategy_tournament.py` (lines 1162–1204).
- Prospective evidence: Frozen at 7/100 blocks. `data/.prospective_shadow_runner.lock` preserved.
- Live trading: `DISABLED`.

