# Independent Research Repair Report — BTCognitive Entry/TP/SL V3

**Date:** 2026-10-09
**Run ID:** None — no experiment was authorized or executed
**Status:** `BLOCKED_AUDIT_FAILURE`
**Decision:** `BLOCKED_AUDIT_FAILURE`
**Model fit / tuning:** None
**Historical holdout outcome values inspected:** No

## Executive summary

Five independent read-only workstreams identified critical implementation and protocol gaps. The frozen barrier grid itself agrees across implementation, outcome contract and preregistration. Follow-up repairs fixed complete close-stamped 15-minute resampling, entry-row selection, elapsed-time/gap resolution under Amendment 01, duplicate entry-slippage charging, and missing-outcome eligibility in the development runner. The pipeline still does not generate reliable confirmatory evidence: historical holdout custody is unverified, and the advertised walk-forward and inferential methods are not implemented as preregistered.

The development run was **not** started. `run_authorization.json` fails closed, the holdout is marked `HOLDOUT_CUSTODY_UNVERIFIED`, and the existing performance metrics remain historical, unverified artifacts. Amendment 01 was approved and implemented without changing frozen contracts. No historical trial record or performance metric was modified.

## 1. Original defects confirmed

Confirmed directly by code/protocol comparison and consolidated in `INDEPENDENT_RESEARCH_AUDIT.md`:

- incomplete and misaligned quarter-hour resampling for close-stamped source rows (repaired after the audit; see addendum);
- entry Open selected from a row whose timestamp does not identify the registered fill-time open;
- duplicate application of entry slippage;
- different engine/oracle gap rules and observed-bar timeout behavior inconsistent with the stated fixed horizon;
- full-history outcome resolution and exit-time scheduling before the research/holdout split;
- holdout start boundary is one day later in code/manifest than in preregistration;
- one index-based train/test partition instead of the registered timestamp walk-forward with purge/embargo;
- null outcome substitution to `-1R`, numeric zero fallbacks for empty selections, and mean-valued confidence bounds for insufficient samples (the runner's label/evaluation path was corrected in the 2026-10-09 addendum below);
- incorrect B0/B0b direction semantics, pair-01-only training reused across the full barrier grid, in-sample outcome-based threshold selection, and uncalibrated logistic probabilities;
- bootstrap, DSR, PBO, multiple-testing, effective-N, ledger run identity and report claims do not match the preregistration or lack required evidence.

## 2. Files changed and why

- `audits/agent_A_data_resolver_audit.md` through `audits/agent_E_provenance_reporting_audit.md`: preserve the five independent read-only workstream findings.
- `INDEPENDENT_RESEARCH_AUDIT.md`: consolidate severity, evidence, root causes, repair ownership, tests, amendment requirement and stop decision.
- `AMENDMENT_REQUIRED.md`: record the conflict between forward-fill semantics and the elapsed-time endpoint without altering frozen contracts.
- `run_authorization.json`, `run_full_research_pipeline.py`, `tests/entry_tp_sl/test_research_run_gate.py`: block model fitting/report regeneration until explicit authorization and test that gate.
- `holdout_custody_manifest.json`: change current custody status from `SEALED_UNTOUCHED` to `HOLDOUT_CUSTODY_UNVERIFIED`, retaining prior metadata and adding the reason.
- `final_research_report.md`, `PROMOTION_DECISION.md`: ensure current status is blocked and no promotion is implied.

At the initial audit stage, no outcome resolver, target, model, barrier, frozen contract, trial-ledger event, or historical metric was changed. The subsequent code repairs and their scope are recorded in the dated addendum below; historical entries and metrics remain unchanged.

## 3. Frozen contract and dataset hashes

- **Frozen contract manifest:** `b6b94d69e576be0357ce9249f24ca05fb44430e6e9050a940054833204e0013f`
- **Dataset SHA-256:** `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`
- Dataset presence and hash were verified by `tests/entry_tp_sl/test_contracts_freeze.py::test_dataset_sha256_matches_manifest`.
- Frozen contracts remain unchanged. No new run-specific hash set exists because no run was made.

## 4. Data and timestamp audit

Manifest claims close-stamped one-minute bars. The new resampler uses right-closed UTC bins, accepts only exactly 15 valid minute rows ending on the quarter-hour, and resets feature/setup windows at any incomplete interval. A read-only check of all `7,766,111` source rows produced `517,740` complete 15-minute bars with zero discontinuities. The entry row is selected at the close timestamp corresponding to the registered fill-time Open, and the first outcome minute is included. No outcome resolution or model execution occurred in this check.

## 5. Label and resolver audit

The initial audit found that the caller fabricated `-1R` for null outcomes, the engine and oracle disagreed on gaps, and entry slippage was charged twice. Resolver parity and cost accounting were repaired in V2 under Amendment 01. The development runner now trains only on finite features and outcomes in resolved states (`TP_FIRST`, `SL_FIRST`, or `TIMEOUT`), excludes invalid observations from evaluation, and leaves unavailable metrics null rather than returning numeric zeros. This D5 repair does not clear other gates; the full experiment remains blocked.

## 6. Actual chronological folds

No valid walk-forward folds were executed in this audit. Existing code uses a single index-based partition (first two quarters of the research-trade list for train, remaining half for evaluation); it does not implement registered expanding/rolling folds or record actual fold UTC dates. Therefore no actual fold dates or valid fold-level estimates can be reported.

## 7. Purge and embargo verification

No registered 240-minute label-overlap purge or 24-hour embargo is applied by the current split. Neither was newly executed or claimed. Required regression: synthetic timestamped trades whose label windows cross fold boundaries must be purged, with post-validation embargo intervals excluded.

## 8. Counts reconciled from raw setup through evaluation

Counts are **not reconciled**. The pipeline has no complete per-stage accounting from detected setups through data eligibility, resolver states, capacity abstentions, train/calibration/threshold samples, outer evaluation, and accepted trades. The report's historical figures are not regenerated or verified here. `20,244` cannot be described as independent accepted trades based on the inspected code.

## 9. Baseline methodology

The current baselines do not match the frozen comparison semantics: random baseline randomizes acceptance but not side; always-long/short masks detector-side outcomes rather than counterfactual outcomes. No corrected baseline results are available.

## 10. Model and threshold-selection protocol

No model was fit. Inspected implementation is pair-01-targeted, reuses the resulting acceptance mask across all pairs, uses in-sample outcome maximization for threshold choice, selects a listed LightGBM configuration by fixed index, and does not calibrate logistic probabilities. The current trial ledger does not record the executed threshold/config on its repeated trial IDs. No model conclusions are valid from this audit.

## 11. Barrier-pair evaluation status

The five IDs and multipliers agree across `FROZEN_BARRIER_GRID`, `outcome_accounting_contract.json`, and `PREREGISTRATION_v1.md`:

| Pair | TP × ATR | SL × ATR | Horizon |
|---|---:|---:|---:|
| 01 | 1.00 | 1.00 | 240 minutes |
| 02 | 1.50 | 1.00 | 240 minutes |
| 03 | 2.00 | 1.00 | 240 minutes |
| 04 | 0.75 | 0.75 | 120 minutes |
| 05 | 2.00 | 1.50 | 240 minutes |

This establishes configuration agreement, **not** correct evaluation. The current pipeline fits only pair 01 and applies its selection mask to the other pairs. Thus all-five-pair registered evaluation is not established.

## 12. Uncertainty and multiple testing

The checked-in functions do not implement the preregistered stationary bootstrap sampling law/resample count on a documented time unit; DSR and PBO are nonconforming proxies; Holm/BH/SPA results are absent despite report claims; empty/short/missing samples can yield numerical fallbacks. No uncertainty or selection-adjusted claim is supportable.

## 13. Trial-ledger integrity

The existing hash-chain event indexes and parent hashes verified during audit, but trial IDs repeat across reruns and model rows do not carry sufficient run-specific provenance. Existing events were preserved; no event was appended. New ledger events already gained a frozen barrier configuration snapshot in prior synchronization work, but a unique run ID and complete provenance binding remain required.

## 14. Holdout custody

Status is `HOLDOUT_CUSTODY_UNVERIFIED`. The historical runner resolved all outcomes and used outcome-derived exit timestamps for scheduling before partitioning. This confirms pipeline access, not human review of specific return values. Do not use this period for further model selection, and do not describe it as pristine/sealed.

## 15. Remaining limitations and unresolved amendment

`AMENDMENT_REQUIRED.md` records the originally unresolved relationship between (a) forward-filling up to three missing minutes and (b) a fixed elapsed-time horizon/timeout endpoint. Amendment 01 now specifies the endpoint and terminal-gap behavior. No frozen contract was edited to resolve it.

Additional confirmed defects in historical holdout custody, folds, baselines, missing outcomes, statistics, and provenance still require isolated implementations plus deterministic regression tests. The explicit run gate remains closed.

## 16. Final promotion decision and claim ladder

| Evidence level | Status |
|---|---|
| Implementation verified | Partial unit tests only; end-to-end data path not verified |
| Experiment executed | Historical artifacts exist; current audit did not execute a run |
| Statistically supported association | Not established by a conforming run |
| Predictive evidence | Not established |
| Positive net economic evidence | Not established |
| Robustness | Not established |
| Selection-adjusted evidence | Not established |
| Prospective evidence | Not established |
| Sealed-holdout evidence | Not established; custody unverified |

**Maximum scientifically justified claim:** no confirmatory predictive or economic claim.
**Final decision:** `BLOCKED_AUDIT_FAILURE`.
**Next gate:** close the remaining P0 repair gates and verify them independently; do not train, tune, regenerate performance tables, or promote before all gates pass.

## Addendum — 2026-10-09: Amendment 01 and deterministic resolver repairs

The user approved `BTC-ENTRY-TP-SL-V3-AMENDMENT-01`, registered as protocol
`BTC-ENTRY-TP-SL-V3.1` with resolver `ENTRY_TP_SL_RESOLVER_V2`. The frozen V1
preregistration, outcome contract, barrier grid, dataset snapshot, and historical
trial-ledger entries were not changed.

Implemented under the amended version:

- Timeout resolution now evaluates the fixed elapsed-minute grid and exits at
  the exact `fill_timestamp + horizon` endpoint.
- Up to three consecutive missing minutes, including leading and terminal
  minutes, are forward-filled flat from the last close; larger gaps fail closed
  as `DATA_GAP`. A leading fill requires a close-stamped prior bar.
- The close-stamped row opening at the registered fill time supplies the entry
  Open and is included as the first outcome-path bar.
- 15-minute resampling now uses exact right-closed UTC quarter-hour boundaries,
  rejects incomplete/invalid groups, and restarts rolling feature and setup
  windows at data discontinuities. The complete source snapshot produced
  `517,740` bars with no quarter-hour gaps.
- Entry price now uses the registered next-bar Open without pre-applying
  slippage; the frozen total round-trip cost, including entry slippage, is
  deducted once.
- New ledger entries and run-scoped reports include amendment, protocol, and
  resolver identifiers.

The full Entry/TP/SL research test suite passes (**109 passed**). No model was
fit, no trial was run, and no performance result was regenerated.
`run_authorization.json` remains `BLOCKED_AUDIT_FAILURE`; historical holdout
custody, chronological validation, missing-outcome handling, baselines, model
selection, and statistical-inference blockers still prevent an experiment run.

The results above establish these repaired code paths only. They do not
establish overall scientific readiness, and the previous audit findings remain
operative where not explicitly repaired here.

## Addendum — 2026-10-09: D5 missing-outcome handling

The development runner no longer substitutes `-1R` for missing or otherwise
ineligible primary-pair outcomes. Training labels require finite features and a
finite net return from `TP_FIRST`, `SL_FIRST`, or `TIMEOUT`; unavailable,
unresolved, invalid, and data-gap states are excluded. Training stops with an
explicit error when no eligible rows exist or either binary class has fewer
than two examples.

Evaluation intersects each acceptance mask with the same resolved-state and
finite-return eligibility rule. It reports excluded unavailable outcomes;
empty selections retain a count of zero, a `NO_ELIGIBLE_SELECTED_OUTCOMES`
status, and null metrics. Confidence intervals are left null below ten eligible
observations and marked `INSUFFICIENT_FOR_BOOTSTRAP`, instead of reusing the
sample mean as a bound. Reports format null-valued metrics as `N/A`.

Deterministic regression tests cover unavailable states, null/NaN/infinite
returns, invalid features, empty selections, insufficient samples, and
mask/return alignment. The full Entry/TP/SL suite passes (**123 passed**).
No model was fit, no trial was run, no report or ledger was regenerated, and
`run_authorization.json` remains blocked. Historical holdout custody,
validation, baseline semantics, model selection, and statistical-inference
blockers remain unresolved.
