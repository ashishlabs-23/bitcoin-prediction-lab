# BTCognitive V36.2 — Existing Outcome Pipeline Audit

## Scope and evidence standard

Read-only inspection of `research/entry_tp_sl/`, the product resolver/evaluator, candidate and risk components, their test sources, manifests, and existing reports. No tests, model fitting, replay, provider calls, or source execution were performed. A test file is evidence of intended test scope, not a passing test. A result report is an authored claim, not independent reproduction.

## Component classification

| Component | Classification | Direct evidence and limits |
|---|---|---|
| Preregistration and frozen decision/entry/cost/outcome contracts | `SPECIFICATION_ONLY` | `research/entry_tp_sl/PREREGISTRATION_v1.md`, `decision_contract.json`, `entry_execution_contract.json`, `outcome_accounting_contract.json`, `instrument_contract.json`, and `detector_spec.py` define the research question, BTC/USD Bitstamp, 15m UTC decision time, PIT cutoff, next-1m-open fill, ATR scale, five barrier pairs, horizon, collision policy, costs, and net-R. The eight declared contract file hashes in `contract_freeze_manifest.json` match the current files. Frozen specification is not runtime correctness. |
| Data intake and rights record | `SPECIFICATION_ONLY` | `data_intake_manifest.json` declares the local 1m CSV, SHA, coverage, UTC bar-close semantics, gap/duplicate policy, and research rights approval. The file is present and hash matches; provenance claims still require lineage and semantic reconciliation. |
| Frozen 6B implementation manifest | `TESTED_UNVALIDATED` | `6B_implementation_manifest.json` claims deterministic parity/property/PIT/cost tests passed and records hashes for resolver sources. Current `reference_resolver.py` and `triple_barrier.py` SHA-256 values do **not** match those recorded hashes. The manifest’s test claims therefore do not establish that the current source was tested. |
| `TripleBarrierEngine` and independent `ReferenceOracle` | `TESTED_UNVALIDATED` | Both implementations exist (`research/entry_tp_sl/triple_barrier.py`, `reference_resolver.py`). Test source covers single touches, collision, timeout, gap, property/differential parity and PIT (`tests/entry_tp_sl/test_triple_barrier.py`, `test_resolver_differential.py`, `test_pit_invariants.py`). Prior reports claim 88 tests, but no current run was permitted and source hashes differ from the 6B manifest. Several contract mismatches below remain. |
| Pilot label sample | `TESTED_UNVALIDATED` | `pilot_labels/pilot_labels_sample.jsonl` contains 500 records; manifest records outcomes and source dataset/contract hashes. The tests assert row count and basic label invariants, not a fresh reproduction or source-to-row-level lineage. Pilot labels are feasibility/debug evidence, not model validation. |
| PIT features | `IMPLEMENTED_UNVERIFIED` | `pit_features.py::compute_pit_features_table` computes rolling features from 15m OHLCV and the current completed decision bar. It sorts by timestamp but does not itself enforce an availability-time cutoff, gap policy, or closed-bar contract; callers must enforce them. |
| A1/A2 setup detector | `IMPLEMENTED_UNVERIFIED` | `setup_detector.py::StructuralSetupDetector.detect_setups` implements same-bar sweep/reclaim and range/reclaim from 15m bars. `detector_spec.py` declares a two-bar A1 reclaim-confirmation window, but the code tests reclaim on the current bar and does not implement that window. The configured cooldown is global to detected events; `last_event_side` is not used. |
| B0–B4 baselines and classifiers | `IMPLEMENTED_UNVERIFIED` | `baselines.py` includes matched acceptance/random, structural, trend, logistic and LightGBM components. B4 targets binary `net_r > 0`, not the required three-class trade outcome. `MetaModelB4LiteLogistic` is described as calibrated, but its `fit` does not apply the imported calibration class. No calibrated B4 artifact is registered. |
| `walk_forward_engine.py` statistical helpers | `BROKEN` | The declared stationary bootstrap uses fixed-length circular blocks, not geometrically sampled stationary blocks; its early `n < 10` branch returns a degenerate interval. The DSR/PBO helper is a simplified two-half proxy, not the preregistered CSCV PBO; it does not use its `benchmark_sr` argument. These outputs cannot support the named inference claims without correction and verification. |
| `run_full_research_pipeline.py` | `BROKEN` | Despite its walk-forward/purge/embargo description, it makes one chronological train/evaluation split, maps missing outcome `net_r` to `-1R`, selects thresholds on training outcomes, does not implement the stated purge/24h embargo, and writes reports, holdout custody, readiness state and trial-ledger records. It must not be rerun as-is. The output counts conflict with other local reports. |
| `holdout_custody_manifest.json` and holdout claim | `BLOCKED` | The manifest declares `SEALED_UNTOUCHED` and 2,662 trades, but the holdout dates are within the same readable 1m CSV; no separate sealed data object/access-control record was established. The pipeline can overwrite this manifest. Treat custody and any holdout claim as unverified. |
| Historical outcome/performance report and trial ledger | `TESTED_UNVALIDATED` | `final_research_report.md`, `PROMOTION_DECISION.md`, and `trial_ledger.jsonl` record prior runs/results. They are inconsistent: the promotion decision reports approximately `+0.01R` to `-0.04R`, while the final report/ledger show B4 at `-0.5678R` BASE and `-1.0954R` CONSERVATIVE; the final report states 20,244 evaluation trades while feasibility materials state 3,842 sequential trades. Some B4 ledger rows are zero-count. No conclusion is reproduced. |
| Product `engine/barrier_resolver.py::DeterministicBarrierResolver` | `BROKEN` for research path outcomes | It uses a different `CandidateSetup` contract and resolver version from the research canonical engine. Its incomplete-path behavior can return a timeout from an early last bar rather than the declared horizon. It is not interchangeable with `TripleBarrierEngine`. |
| `engine/trade_outcome_evaluator.py::TradeOutcomeEvaluator` | `BLOCKED` | Correctly fails closed with `META_MODEL_UNAVAILABLE` when three outcome probabilities are absent. It is not backed by a validated calibrated three-class artifact. Additional probability range, finite-value, calibration, and model/contract identity checks are not established by this inspection. |
| `engine/entry_contracts.py` and product smart-entry path | `IMPLEMENTED_UNVERIFIED` | Separate immutable product contract and `DeterministicBarrierResolver`; candidate fields require probabilities, but the existing product pipeline supplies `None` and abstains. Do not mix with research labels/cost conventions. |
| Hourly `engine/strategy_signal_engine.py` | `TESTED_UNVALIDATED` | Candidate generators and related tests exist. Their hourly Donchian/Bollinger and Parkinson-volatility contracts differ from the frozen 15m A1/A2 and ATR14/next-1m-fill Entry/TP/SL workstream. They do not generate V36.2 research labels as-is. |
| Risk budget and execution-cost helpers | `IMPLEMENTED_UNVERIFIED` | `engine/risk_budget.py` provides account budget/state gates; `engine/execution_cost_model.py` contains other cost/collision helpers. They are not the research track’s frozen Bitstamp BASE/CONSERVATIVE 35/65 bps cost contract and must not silently replace it. |
| Calibrated `TP_FIRST` / `SL_FIRST` / `TIMEOUT` model | `BLOCKED` | No verified three-class model/artifact exists. The existing binary B4 models do not estimate the three required outcome probabilities. |

No component qualifies as `RESEARCH_VALIDATED` under this audit’s bar. The final research report contains a retrospective finding, but source/result/holdout inconsistencies prevent treating its performance or claim level as validated. The frozen specifications and contract hash agreement are useful, not sufficient, evidence.

## Do the frozen contracts define entry, barriers, horizon, ambiguity, costs, and accounting?

Yes, at specification level:

| Item | Frozen definition |
|---|---|
| Instrument and source | BTC/USD spot, Bitstamp; 1m OHLCV path data. |
| Candidate decision | Completed 15m UTC bar at `t0`; features use data available by `t0`. A1/A2 side is structural setup output. |
| Entry | Taker fill at next 1m bar open, `t0+60s`; missing fill fails closed; entry gap >2% cancels; gap fills at actual open. |
| Volatility scale | Primary `ATR_14(15m)/Close_t0`; secondary 96-return 15m realized-volatility definition. |
| Stops/targets | Frozen five-pair TP/SL multiplier grid; primary 1x/1x. Barriers use entry price and `sigma_t0`. |
| Horizon | Primary 240 1m path bars / 240 minutes; secondary 120 minutes. |
| Ambiguity | Same-1m dual touch resolves conservative SL-first and records collision/unresolved order; TP-first sensitivity is required. |
| Costs | Scenario assumptions: 35 bps BASE and 65 bps CONSERVATIVE round trip, with fee/slippage/half-spread components. They are not measured live fills. |
| Accounting | 1R is entry-stop distance; TP/SL return multiples; timeout uses actual exit close, not hardcoded -1R; net R deducts costs; one position per instrument. |

Specification completeness does not mean the implementation follows each clause. Observed implementation conflicts include:

1. `build_trade_contract` adjusts the fill price for entry slippage, while the resolver also deducts a total round-trip cost fraction that already includes entry slippage. This appears to charge entry slippage twice unless a different price/cost interpretation is intended; resolve before accepting economics.
2. The frozen >2% entry-gap cancel rule has no decision-close/gap input in `build_trade_contract`, so the rule is not enforced by the research builder.
3. `TripleBarrierEngine.resolve` tests same-bar dual-touch before resolving which barrier was crossed at the opening gap. A bar opening beyond TP and later touching SL can be labeled SL-first, although the open itself establishes the earlier TP crossing.
4. The resolver tolerates up to three missing path bars, uses row count rather than elapsed-time boundary to stop path collection, and can accept an early timeout with a shortened path. This conflicts with exact vertical-horizon semantics.
5. The required TP-first sensitivity is specified but not established in the current evaluation script.

These are contract/code reconciliation blockers, not a reason to create a second resolver or alter the frozen contract silently.

## Reconciliation with V36.1 design

V36.1 was directionally consistent in proposing a candidate stage followed by a conditional three-class outcome model and explicitly keeping the model untrained. The audit finds:

- The existing workstream already has frozen definitions for candidate cadence, ATR scale, entry fill, barrier grid, costs, timeout, and ambiguity. V36.1 must reuse them rather than create a parallel parameterization.
- V36.1 referenced `engine/barrier_resolver.py` as prior outcome groundwork. That is not the V3 research authority; `research/entry_tp_sl/triple_barrier.py::TripleBarrierEngine` is the track-specific canonical implementation according to its reachability record.
- V36.1’s phrase “approved setup logic” overstates status: A1/A2 are frozen research detector rules, not an approved production strategy or validated source of edge.
- Existing B4 is binary accept/reject, not a three-class outcome model. Any new probability system is blocked until the existing contract, labels, splits, and pipeline are reconciled; do not duplicate or train another model in this milestone.
- V36.1’s explicit historical-replay constraints remain applicable: no current-time leakage, no synthetic event data, no writes to protected ledgers/databases, no execution authorization.

## Reuse decision

Reuse the V3 research contract, local Bitstamp 1m snapshot, A1/A2 detector, PIT feature builder, canonical `TripleBarrierEngine`, and independent oracle **as the existing starting point**, not the product `engine/barrier_resolver.py`. Do not reuse the existing published model-performance estimates, current split/evaluation harness, or holdout status as validated evidence. The existing pipeline is not presently safe to execute because it can overwrite protected research artifacts and its current evidence does not reconcile to source.
