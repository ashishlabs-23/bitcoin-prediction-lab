# Entry/TP/SL Timing Provenance Gate Report

**Inspection date:** 2026-11-04  
**Scope:** Timestamp-source documentation and pipeline code review. No data rows or holdout values were inspected, and no labels were generated.

## Findings

- `research/entry_tp_sl/dataset_manifest.template.json` declares timestamp role `unknown`, timestamp semantics `UNVERIFIED`, and no availability-time rule.
- `research/entry_tp_sl/data_intake_manifest.json` records a verified local snapshot and a `VERIFIED_60S_BAR_CLOSE` PIT status, but does not establish a raw `Timestamp` role or availability-time field/rule. This conflict does not establish admissible timing provenance.
- `research/entry_tp_sl/PREREGISTRATION_v1.md` defines the decision time as the close of a completed 15-minute bar. The pipeline uses the last constituent raw `Timestamp` as the resampled decision time and later generates outcomes, so it must not proceed while the raw timestamp mapping and availability remain unresolved.

## Fail-closed behavior

`run_full_research_pipeline.run()` now unconditionally raises before `pandas.read_csv`: there is no repository-controlled, evidence-backed timing authorization. The function accepts no timing-contract argument or authorization override; a caller-constructed `PITTimingContract(verified=True)` is rejected at the call boundary and cannot authorize reading the real CSV, resampling, outcome generation, ledger appends, or report writes. Dedicated tests verify `pd.read_csv` is not called either for the no-authorization call or when such an argument is attempted.

`compute_pit_features_table()` independently validates an explicit contract and rejects missing timing columns, invalid/duplicate/non-monotonic timestamps, and future availability. This supports isolated synthetic-fixture tests of causal feature calculations only; a caller-supplied fixture contract does not authorize the production pipeline or market data access.

## Resampling boundary — blocked

The existing pipeline contains a 15-minute `resample('15min')` operation without explicit `label`, `closed`, or `origin` arguments, and aggregates the raw `Timestamp` with `last`. These implementation choices are **not approved timing semantics**. No replacement semantics are inferred or introduced. The resampling boundary, decision-time mapping, and availability aggregation remain blocked pending authoritative source evidence and an owner-approved timing contract. The production pipeline cannot reach this code while authorization is absent.

## Unresolved owner decisions

1. Establish authoritative source evidence for the raw timestamp role and its relationship to each bar's close.
2. Establish an authoritative availability-time field and rule for this exact dataset, or explicitly approve a documented point-in-time mapping without changing frozen contracts/manifests in this remediation.
3. Decide and document the resampling boundary (`label`, `closed`, `origin`), raw-to-decision timestamp mapping, and availability aggregation from source evidence; do not infer them from current code defaults.
4. Reconcile conflicting repository provenance statements through an auditable owner decision before any data access for label generation.

Until those decisions are documented and passed as a verified contract, the research pipeline intentionally refuses to start.
