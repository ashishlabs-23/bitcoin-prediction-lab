# BTCognitive V35.0 — Repository Hygiene, Provenance Audit, and Quarantine Integrity

**Milestone:** BTCognitive V35.0 — Research Product Finalization and Project Closure  
**Date:** 2026-11-03  
**Status:** COMPLETE / GOVERNED  
**Lead Coordinator:** Engineering Lead & Data Governance Auditor  
**Governed Assessment:** `REPOSITORY_HYGIENE_VERIFIED` | `INTEGRITY_PRESERVED`

---

## 1. Executive Summary

Milestone V35.0 conducted a final repository-wide provenance and quarantine audit to ensure that all historical research artifacts, quarantined model implementations, cryptographic dataset hashes, and operational boundaries remain intact and fully auditable without unapproved modifications.

### Audit Checklist Highlights
1. **Git State Verification:** Branch `main`, HEAD commit `25d483f` (`ahead 1` vs `origin/main`). Zero unapproved commits, zero pushes, and zero destructive resets (`git checkout .`, `git reset --hard`) were performed.
2. **Dataset Hash Immutability:** Both historical Bitstamp segments (2024 slice and 2026 slice) maintain identical SHA-256 hashes.
3. **Quarantine Integrity:** Non-viable models (`Chronos-2`, `Hawkes process`, `Mamba SSM`) remain strictly locked in quarantine manifests with zero production execution paths.
4. **Ledger Immutability:** Prospective ledgers in `data/` remain unmutated, with background collectors permanently inactive.

---

## 2. Dataset Cryptographic Fingerprints & Provenance

| Dataset Asset | Workspace File Path | Row Count | SHA-256 Cryptographic Hash | Integrity Status |
| :--- | :--- | :--- | :--- | :--- |
| **Historical Segment 1 (2024)** | `data/providers/bitstamp/BTCUSD_1h_v34_2_multiyear.parquet` | 1,000 | `811c9704629d3b735643c0d931ad1998cf0604e9dd96b9790aaf1241ee807436` | **IMMUTABLE / VERIFIED** |
| **Historical Segment 2 (2026)** | `data/providers/bitstamp/BTCUSD_1h_v34_expanded.parquet` | 4,000 | `9e8d92a2db78a5c71737146713541c3db5f27d398684114f09d5db3a4493ec81` | **IMMUTABLE / VERIFIED** |
| **Fresh Bitstamp Cache (Live)** | `data/providers/bitstamp/BTCUSD_1h.parquet` | 1,000 | `a80ba771968ac7ccc8284f6e7543fddbadd89a6bbc40673799c47b6a044a0c5d` | **FRESH / CAUSAL** |
| **Baseline Pytest XML** | `baseline_pytest.xml` | N/A | Preserved in workspace root | **PRESERVED** |

---

## 3. Quarantined Assets & Manifest Verification

All models failing empirical or operational gates are isolated in formal quarantine manifests:

| Quarantined Component | Manifest Location | Failure Reason | Operational Constraint |
| :--- | :--- | :--- | :--- |
| **Chronos-2 Foundation** | `results/model_change_request.json` | Excessive inference latency (>15s), zero directional advantage | Prohibited from runtime serving |
| **Hawkes Microstructure** | `research/hawkes_shadow_report.md` | Extreme parameter instability during volatility spikes | Excluded from signal pipeline |
| **Mamba State-Space Model** | `results/mamba_trial_manifest.json` | High compute overhead on CPU, unstable gradient convergence | Quarantined in offline experimental branch |
| **C2 Conformal Bands** | `experiments/results/v34_4_research_results.json` | Empirical undercoverage (78.02% vs 90%), 168h feedback delay | Suppressed in UI/API (`UNAVAILABLE`) |

---

## 4. Prospective Ledger & Process Safety

1. **Background Processes:**
   - Active process: Standalone uvicorn server running on `0.0.0.0:8000` (task-10341).
   - Zero high-frequency or unauthenticated collectors are running.
   - Lock file `data/.prospective_shadow_runner.lock` remains clean.
2. **Ledgers Preserved:**
   - `data/prospective_forecast_ledger.jsonl`: Unchanged.
   - `data/prospective_entry_ledger_v2.jsonl`: Unchanged.
   - `data/prospective_entry_ledger_v1_quarantined.jsonl`: Preserved for historical auditability.

---

## 5. Git Worktree Verification

```
Branch: main (ahead 1 vs origin/main)
HEAD Commit: 25d483f feat(research): implement first-passage baseline, default abstain gate, gap backfill, and directional retest
Previous Commit: 24092a1 test(regression): restore V9-V29 full regression suites, conftest, and gate tests
```

- **Clean Boundary:** All edits made in V35.0 are strictly localized to:
  - Deprecation labeling in `engine/regime_strategy_tournament.py` and `web/app.js`.
  - Tardis sample parser additions in `engine/market_data_adapters/tardis_sample_parser.py` and `tests/test_v35_tardis_sample_parser.py`.
  - Research reports in `research/reports/offline_mvp/20261103_350000_v35_0_project_closure/`.
- No user-modified files were reverted or discarded.

