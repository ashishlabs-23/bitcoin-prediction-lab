# BTCognitive V33.8 — Governed Repository Cleanup Manifest & Quarantine Audit

**Document ID:** `V33_8_CLEANUP_MANIFEST.md`  
**Milestone:** V33.8 Final Stabilization  
**Date:** November 2, 2026  
**Auditor Lead:** Senior Engineering Lead & Technical Debt Auditor  
**Contributing Agents:** Agent 7 (Repository Cleanup & Dependency Auditor)  
**Governance Scope:** OFFLINE_RESEARCH_ONLY  

---

## 1. Executive Summary

In adherence to the BTCognitive Permanent Operating Contract (Prime Directive & Epistemic Boundaries), this manifest documents the safe isolation and governance classification of all untracked and auxiliary files in the repository.

Key cleanup actions executed:
1. **Quarantine Staging Directory (`quarantine_v33_8/`):** Created to safely isolate disposable files without performing irreversible git operations (`git reset`, `git clean`).
2. **Zero Breaking Runtime Dependencies:** Confirmed via static analysis that zero files in `quarantine_v33_8/` are imported or required by active services.
3. **Protected File Verification:** All active ledgers (`data/`), model weights (`models/`), research reports (`research/`), and regression tests (`tests/`) are strictly protected and preserved.

---

## 2. Quarantine Master Manifest

| File / Folder Path | File Size | Classification | Isolation Status | Safety Audit Justification |
|---|---:|---|---|---|
| `scripts/patch_analysis_id_dom.py` | 686 B | DISPOSABLE | Staged in `quarantine_v33_8/scripts/` | Ephemeral one-off patch; 0 incoming imports |
| `scripts/patch_app_v33_4m.py` | 7.6 KB | DISPOSABLE | Staged in `quarantine_v33_8/scripts/` | Ephemeral one-off patch; 0 incoming imports |
| `scripts/patch_app_v33_4m_r.py` | 4.5 KB | DISPOSABLE | Staged in `quarantine_v33_8/scripts/` | Ephemeral one-off patch; 0 incoming imports |
| `scripts/patch_app_v33_5.py` | 5.2 KB | DISPOSABLE | Staged in `quarantine_v33_8/scripts/` | Ephemeral one-off patch; 0 incoming imports |
| `scripts/patch_expose_res.py` | 1.1 KB | DISPOSABLE | Staged in `quarantine_v33_8/scripts/` | Ephemeral one-off patch; 0 incoming imports |
| `scripts/patch_falsy_freshness.py` | 752 B | DISPOSABLE | Staged in `quarantine_v33_8/scripts/` | Ephemeral one-off patch; 0 incoming imports |
| `scripts/patch_outcome_ids.py` | 837 B | DISPOSABLE | Staged in `quarantine_v33_8/scripts/` | Ephemeral one-off patch; 0 incoming imports |
| `scripts/patch_sqlite_resilience.py` | 10.2 KB | DISPOSABLE | Staged in `quarantine_v33_8/scripts/` | Ephemeral one-off patch; 0 incoming imports |
| `scripts/patch_target_ref.py` | 832 B | DISPOSABLE | Staged in `quarantine_v33_8/scripts/` | Ephemeral one-off patch; 0 incoming imports |
| `tmp_chrome_profile/` | 1.05 MB | DISPOSABLE | Staged in `quarantine_v33_8/tmp_chrome_profile/` | Stale Crashpad metrics and profile cache |
| `BTCognitive/BTCognitive/` (nested) | 324 KB | DISPOSABLE | Staged in `quarantine_v33_8/nested_BTCognitive/` | Duplicate nested folder containing stray PNG |
| `data/.prospective_shadow_runner.lock` | 102 B | DISPOSABLE | Staged in `quarantine_v33_8/` | Stale lock for dead PID 31676 from Oct 23 |

---

## 3. Preservation Governance: Protected File Inventory

The following categories were explicitly audited and confirmed as strictly protected from deletion or quarantine:

1. **Active Core Execution Code:**
   - `api/server.py`, `api/routes_*.py`
   - `engine/htf_setup_detector.py`, `engine/bitstamp_market_data_service.py`
   - `engine/historical_evidence_loader.py`, `engine/canonical_regime_map.py`
2. **Authoritative Research Evidence & Reports:**
   - `research/reports/offline_mvp/`
   - Historical trade ledgers: `data/research/htf_trades.json`
   - Prospective log: `data/prospective_forecast_ledger.jsonl`
3. **Regression Test Suite:**
   - All 52 untracked and tracked test modules in `tests/`.

---

## 4. Audit Conclusion

The repository is fully cleaned and stabilized without violating the Non-Destructive Git Directive. All ephemeral debris is quarantined and accounted for.

