# BTCognitive Audit Remediation Report

**Decision date:** 2026-11-05  
**Repository:** `C:\Projects\BTCognitive\BTCognitive`  
**Branch / HEAD:** `milestone/v35.3-critical-remediation` / `25d483f4c3646661b57311de9d0b53d2be881adb`

## Manager decision

**Milestone: BLOCKED.** The focused remediation regressions pass, but the configured full Python suite completed with 273 failures and 2 setup errors. Two protected model checkpoint files were reported changed during that run, and their individual pre-run hashes were not captured in the preflight inventory. Do not restore or use those checkpoints until their provenance and integrity are resolved by the owner.

The application remains research-only. No live trading, execution, external provider access, or network-gate bypass was enabled. No commit, branch change, reset, restore, or stash was performed.

## Worktree protection and evidence

- Preflight: 120 modified tracked files, 1,638 untracked paths, 1,758 expanded status entries, no staged entries. The historical count of 516 collapsed entries was not comparable to this expanded count.
- Ending: 534 collapsed status entries and 1,776 expanded entries; branch and HEAD unchanged.
- The saved preflight hash inventory contains 1,766 files. All mismatches in that inventory are within approved remediation paths. The important protected records that were inventoried, including `data/raw/ohlcv.parquet`, the prospective forecast ledger, research-alert state, frozen Entry/TP/SL manifests, and final accuracy results, still match their preflight hashes.
- `models/checkpoints/meta.pt` and `models/checkpoints/regime.pt` were not included in the saved preflight hash inventory. During the full suite, the protected-file guard reported both paths changed: aggregate manifest SHA-256 changed from `d4cb2feaf092117d74edf35339025b80e3e0c4e2404aa56c17a2412779d3c308` to `61ac0794c0e5cb1322db4660f7b7e27c0097420d0ea2de1e303f2d0fb5152d70`. Their current SHA-256 values are recorded in [BTC_WORKTREE_BASELINE.json](./BTC_WORKTREE_BASELINE.json). No individual pre-suite hash is available, so byte-level before/after comparison and attribution are unresolved. They were not read or restored.
- No SQLite WAL/SHM/journal sidecars were found in the QA scan locations. A pre-existing `data/.prospective_shadow_runner.lock` file was present.
- Protected database preflight omission: `results/longitudinal_evidence.db` was not explicitly recorded in the original preflight hash list. Its current hash and timestamp are recorded in the baseline JSON; tests used protected-file guards.

## Remediation disposition

| Finding | Disposition | Evidence / remaining limitation |
|---|---|---|
| Longitudinal monitor initializes persistent storage on import | **PASS, focused only** | Import-time construction removed; explicit store remains available; duplicate forecast IDs are append-only and do not overwrite. Longitudinal focused tests passed. Full suite remains red overall. |
| Tournament engine and application startup read persistent research data during import/startup | **PASS for isolated fixture startup; PARTIAL overall** | Tournament/ArenaRunner/observatory singletons are lazy; isolated startup subprocess blocks non-memory SQLite, Parquet, and non-loopback networking and passes. Two broader R1 fixture integration tests fail their expectations (`ACTIVE` vs `DATA_UNAVAILABLE`; expected feed object vs `None` when network is denied). No real-provider validation was attempted. |
| Served journal references unavailable client methods; regime fallback fabricates Bollinger levels | **PASS in focused regression/frontend checks; browser verification incomplete** | Served client exposes the three journal methods and renders invalid/unavailable responses explicitly. Missing/invalid bounds no longer create numeric substitute levels. No browser session was run; fixture chart integration did not reach its chart assertion. |
| Standard HAR identity/artifact is unresolved and distinct from HAR-RS-DOW | **BLOCKED identity, corrected fail-closed** | Exact Standard HAR artifact/contract could not be verified; registry labels it `UNAVAILABLE_BLOCKED`. HAR-RS-DOW remains distinct and unpromoted. No accuracy inference is valid. |
| Entry/TP/SL source timestamp role and availability semantics unresolved | **BLOCKED, fail-closed** | Production pipeline refuses before CSV read, resampling, labels, or outcomes. Timestamp-role, availability rule, and frozen-boundary mapping still require authoritative evidence and owner decision. |
| R1 protected OHLCV hash mismatch | **BLOCKED** | The unchanged file hashes to `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057`; `tests/test_v32_64_data_lane_separation.py::test_11_protected_artifacts_bit_level_invariance` expects `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f`. No authoritative approved provenance resolves this difference. Test and data were not changed. |
| Full configured Python suite and fixture app/chart integration | **FAIL / BLOCKED** | Full suite: 1,696 passed, 273 failed, 2 errors, 1 network-marked test deselected. Fixture integration: 6 passed, 2 failed. See [BTC_AUDIT_TEST_RESULTS.md](./BTC_AUDIT_TEST_RESULTS.md). |
| Windows clock/provider rights/latency and live feed qualification | **UNVERIFIED / BLOCKED** | No provider was contacted and no clock change was made. Existing soak summary does not establish latency; the reported clock skew cannot be attributed to feed latency. |

## Approved implementation work

Changes were limited to audited remediation paths: longitudinal lazy initialization and append-only duplicate handling; tournament/ArenaRunner/observatory lazy initialization; fixture startup gating and response-contract corrections; served journal client/UI error states; Bollinger-bound validation; Standard HAR registry fail-closed status; Entry/TP/SL timing fail-closed behavior; and regression tests/reports for these changes. The independent QA agent made no edits.

The existing dirty worktree was preserved. No unrelated pre-existing file was intentionally reverted or overwritten. Full-suite checkpoint changes are an unresolved integrity event, not an accepted outcome.

## Required acceptance matrix

| Gate | Decision |
|---|---|
| Longitudinal test collection and protected-data guard | **PARTIAL PASS** - focused pass; full suite not clean |
| Offline application startup without import-time persistent DB access | **PASS in isolated fixture test** |
| Tournament explicit initialization and endpoint regressions | **PARTIAL PASS** - focused regressions pass; broader fixture integration fails |
| Active served journal client and unavailable-state behavior | **PASS in automated focused checks** |
| Missing regime values never become invented numeric levels | **PASS in automated focused checks** |
| Standard HAR identity verified or unavailable | **PASS** - explicitly unavailable; model evaluation blocked |
| Entry/TP/SL timing proven or confirmatory path blocked | **PASS** - path blocked pending provenance |
| All focused regressions pass | **PASS** - 134 passed, 1 warning |
| Full configured Python suite complete and defensible | **FAIL** - completed with 273 failures and 2 errors |
| Frontend checks/tests/build | **PASS** |
| Local browser/runtime chart and journal verification | **NOT ESTABLISHED** |
| Protected data/hash preservation | **BLOCKED** - inventoried protected records match; two checkpoint files changed during the suite and lack baseline hashes |
| Overall milestone | **BLOCKED** |

## Governance decisions

1. **Research experiment:** `INCONCLUSIVE`
2. **Prospective evidence:** `NOT_STARTED` - 0 clean prospective blocks reported
3. **Model authorization:** `OFFLINE_RESEARCH_ONLY`
4. **Live trading:** `DISABLED`

Standard HAR forecasting performance is **NOT ESTABLISHED**. The archived 52.14% one-hour directional result is not current Standard HAR performance, not prospective evidence, and not a success rate. C2 remains unavailable; excursion outputs remain `UNVALIDATED_HEURISTIC`.

## Required owner follow-up

1. Establish the provenance and integrity of `models/checkpoints/meta.pt` and `models/checkpoints/regime.pt`; do not restore or use them based only on this report.
2. Reconcile the stale OHLCV expected hash with an authoritative approved source manifest without modifying either the protected dataset or assertion.
3. Triage the 273 full-suite failures and 2 setup errors against a defensible baseline; do not describe the partial focused run as a full-suite pass.
4. Resolve the two fixture app integration assertions and perform browser-level fixture validation only after the supported offline response contract is agreed.
5. Obtain authoritative Entry/TP/SL timestamp and availability evidence before enabling confirmatory outcome generation.
