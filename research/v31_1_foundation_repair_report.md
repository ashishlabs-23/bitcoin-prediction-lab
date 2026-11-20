# BTCognitive V31.1 — Foundation Repair Report

**Review date:** 2026-10-23  
**Repository:** `C:\Projects\BTCognitive\BTCognitive`  
**Initial branch / HEAD:** `main` / `24092a118bb4285cb2675cbc02694d34800d92d5`  
**Scope:** Offline historical-replay foundation review only. No strategy tournament, model fitting, threshold tuning, live prediction, order placement, or collector operation.

## 1. Decision and evidence summary

### `BLOCKED — DATA PROVENANCE OR RIGHTS UNRESOLVED`

No candidate dataset clears Gate A as documented in the repository. The Bitstamp 1-minute file has a verified local hash and passes structural checks, but source timestamp/availability semantics and the conflicting rights/provenance records remain unresolved. Coinbase BTC-USD 15-minute data has an identifiable source and bucket-start timestamps, but its use terms have not been approved in the snapshot record, it has no persisted per-row availability time, and it cannot supply the preregistered 1-minute path. The Binance BTCUSDT hourly source is mislabeled as Coinbase BTC-USD in V12 and has no accepted V31.1 manifest.

Following the required stop rule, no replay or cost implementation was changed, no frozen input manifest was created, and no strategy performance work was run. Existing replay, cost, and statistical issues are recorded below as blockers; they are not represented as repaired.

## 2. Initial versus final workspace integrity

| Check | Initial snapshot | Final check |
|---|---|---|
| Branch and HEAD | `main`; `24092a118bb4285cb2675cbc02694d34800d92d5` | `main`; same HEAD; no branch or commit was created. |
| Pre-existing dirty inventory | 53 changed paths were present before V31.1 work. Preserve all. One prior dirty `results/mamba_dataset_manifest.json` change was reported missing before this milestone; its former content/provenance is unknown and was not reconstructed. | No existing file was reverted, reset, stashed, cleaned, or overwritten. The three V31.1 documents below are the only newly created paths; existing changes remain user-owned. |
| Python / pytest processes | No running Python/pytest process was found in the V31.1 baseline inspection. The prospective collector was inspected read-only; it was not started, stopped, restarted, or reconfigured. | No tests were launched in this milestone. No processes were killed. |
| `data/prospective_entry_ledger.jsonl` | 5 lines; recorded baseline string `91C3AED984002F611A59C78A2EB4C342C0970BAEBBD2E3D6DF7973BE7AC4D7` contains only 62 hexadecimal characters and is not a valid SHA-256. | 5 lines; current SHA-256 `91C3AED984002F611A59C78A2EB4C342C0970BAEBBD2E3D6DF7973BE7ACF1DD7`. Current bytes normalize exactly to the HEAD blob (the 5-byte difference is CRLF checkout line endings). The invalid initial digest prevents a direct hash-equality claim. |
| `data/prospective_shadow_v1.jsonl` | 0 lines; SHA-256 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` | 0 lines; same SHA-256; no writes were made. |

The captured initial `git status --short` inventory (53 paths) was:

```text
 M CHANGES.md
 M README.md
 M data/prospective_forecast_ledger.jsonl
 M data/research_alert_state.json
 M engine/probabilistic_entry_engine.py
 M experiments/results/multi_regime_validation_report.json
 M experiments/results/post_repair_milestone_5_lock.json
 M experiments/results/stage10_shadow_validation/shadow_prediction_ledger.jsonl
 M experiments/results/stage11_forward_validation/forward_prediction_ledger.jsonl
 M research/baseline_challenge_report.md
 M research/challenger_bakeoff_report.md
 M research/hawkes_latency_report.md
 M research/hawkes_shadow_report.md
 M research/independent_block_report.md
 M research/information_inventory_report.md
 M research/interval_sharpness_report.md
 M research/live_baseline_comparison.md
 M research/live_long_validation_report.md
 M research/live_metric_reconciliation_report.md
 M research/production_review_block_10.md
 M research/range_stability_report.md
 M research/reports/post_repair_5_block_observed.md
 M research/reports/post_repair_baseline.md
 M research/reports/post_repair_restart_review.md
 M research/reports/pre_post_repair_comparison.md
 M results/challenger_bakeoff_manifest.json
 M results/live_validation_manifest.json
 M results/mamba_trial_manifest.json
 M results/model_change_request.json
?? data/.prospective_shadow_runner.lock
?? data/prospective_shadow_status.json
?? data/prospective_shadow_v1.jsonl
?? engine/barrier_resolver.py
?? engine/entry_contracts.py
?? engine/prospective_shadow_collector.py
?? engine/shadow_feed_runner.py
?? research/protocol_v1_1.md
?? research/protocol_v1_2_proposal.md
?? research/v30_3_prospective_shadow_report.md
?? research/v30_4_shadow_feed_report.md
?? research/v30_5_shadow_operations_report.md
?? research/v30_6_operational_proof_report.md
?? research/v30_7_shadow_burnin_report.md
?? research/v30_8_collection_integrity_report.md
?? research/v30_9_statistical_gate_audit.md
?? research/v31_0_research_closure_report.md
?? tests/test_entry_contracts_and_resolver.py
?? tests/test_prospective_shadow_collector.py
?? tests/test_shadow_feed_runner.py
?? tests/test_v30_6_operational_proof.py
?? tests/test_v30_7_shadow_burnin.py
?? tests/test_v30_8_collection_integrity.py
?? tests/test_v30_9_statistical_gate_audit.py
```

Final `git status --short` is that inventory plus the three V31.1-created files: `research/v31_1_data_provenance_audit.md`, `research/v31_1_foundation_repair_report.md`, and `research/protocol_v1_2_decision_matrix_v31_1.md`. The proposal and `CHANGES.md` were already dirty at baseline and were only appended for this milestone.

V31.1 edited only documentation: added `research/v31_1_data_provenance_audit.md`, `research/v31_1_foundation_repair_report.md`, and `research/protocol_v1_2_decision_matrix_v31_1.md`; appended a dated, explicitly unapproved decision-matrix section to `research/protocol_v1_2_proposal.md`; and added this milestone's documentation-only entry to `CHANGES.md`. Frozen V1.1, prospective ledgers, replay code, cost code, tournament code, and production state were not edited.

## 3. Dataset identity and limitations

The detailed candidate-by-candidate evidence and source links are in `research/v31_1_data_provenance_audit.md`.

- **Bitstamp BTC/USD 1-minute CSV:** 393,952,273 bytes, 7,766,111 rows, SHA-256 `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`, range 2012-01-01 00:01:00 UTC to 2026-10-07 03:11:00 UTC. A read-only full-file scan found zero null cells, invalid OHLC rows, duplicate timestamps, nonpositive timestamp steps, or non-60-second steps. These checks do not establish timestamp event role or historical availability. The local snapshot claims Kaggle version 745, while current public metadata reports version 759; the exact mapping of this hash to version 745 is not corroborated by the current metadata. The publisher updater confirms a Bitstamp 60-second API source but carries timestamps without defining their bar boundary. `data_intake_manifest.json` says 60-second bar-close/PIT verified and research approved; `provenance.template.json` still marks the timestamp role, available-time rule, and license review unverified; `G0_FOUNDATION_INTEGRITY.md` records unresolved semantics/rights, while the later G0 closure declares them passed. The conflict is preserved, not silently resolved.
- **Coinbase BTC-USD 15-minute parquet:** 9,000 rows, 464,798 bytes, SHA-256 `7fcd61d21a995c251688e6ae687fa1678f0bec7bfb5cf08ea87f5ebb6f9d1091`; 2026-07-21 20:15 UTC to 2026-10-23 14:00 UTC. Coinbase documents `time` as bucket start; the adapter's stored timestamp is not an availability time, and its `last_completed_candle_utc` label reports the bucket start. Terms/use approval is absent from this snapshot's manifest. Its granularity is not the preregistered 1-minute path.
- **Binance BTCUSDT hourly parquet:** ingestion identifies Binance BTCUSDT and assigns `available_time` one hour after the timestamp; V12 labels its data Coinbase BTC-USD. This instrument mismatch, absent V31.1 frozen input identity/rights record, and hourly granularity disqualify it as a substitute.
- **Funding:** No historical funding input with verified provenance, timestamps, and join semantics was accepted. Configured assumed rates are not historical evidence.

No accepted dataset manifest was created.

## 4. Replay and cost findings — unchanged

No code repair was authorized after Gate A failed. Source audit found these remaining defects/limitations:

- `engine/entry_contracts.py` compares ISO timestamp strings lexically and permits `fill_timestamp_utc == decision_timestamp_utc`. `compute_candidate_id` omits venue, product, cost scenario, feature hash, and model identity.
- `engine/barrier_resolver.py` relies on supplied bar order, does not validate OHLC bounds/duplicate chronology/gaps, and can report timeout from an exhausted but incomplete path. This is not a validated common-window replay contract.
- `research/v12_strategy_tournament_engine.py` has a candidate path using the full 4-hour frame rather than the common holdout; the declared `MATCHED_RANDOM_ENTRY` baseline is not returned in the evaluated result; and default wall-clock timestamps prevent byte-identical results. Its Binance perpetual scenario is applied to spot-path data in parts of the runner.
- `engine/execution_cost_model.py` has incompatible legacy and class-based two-sided calculations. Under the configured Coinbase assumptions, the legacy method's 47 bps is one taker fee (40) + two-sided spread (3) + two-sided slippage (4), while the class method's 87 bps is two taker fees (80) + spread (3) + slippage (4). The legacy method's name implies round-trip but omits the exit fee.
- Binance configured costs are assumptions, not observed execution. The class method adds the configured 1 bps per 8-hour interval only via `floor(holding_hours / 8)`. The V12 15 bps fixed scenario and candidate-D fixed cost are not a verified timestamped funding join. Spread, slippage, maker fills, adverse selection, and actual fee tier are unobserved in the available OHLC data.
- Spot and perpetual futures remain different products. No cost code was modified and no cost scenario was selected for V31.1.

## 5. Statistical protocol and human review

V1.1 remains frozen; the V1.2 proposal remains unapproved. A decision matrix has been added to `research/protocol_v1_2_decision_matrix_v31_1.md` and appended to the existing proposal. It recommends calendar-time, aligned net return difference as the primary strategy-performance estimand, with per-setup net R and barrier/excursion measures secondary. It distinguishes completed eligible outcomes from pending/excluded records and rejects interpreting a bootstrap block length as an effective sample-size multiplier.

No fixed number of trades, blocks, or effective observations is justified here. The human protocol owner must choose the economically relevant minimum effect, uncertainty/precision target, dependence model, interval method, benchmark, allocation policy, and interim-look rule before a confirmatory gate can be specified. DM-HLN is reserved for aligned forecast-loss differentials with a specified horizon, not treated as generic inference for variable-duration trade P&L. PBO/CSCV and Deflated Sharpe remain secondary diagnostics subject to their assumptions; none repairs leakage or invalid inputs.

## 6. Test commands and results

- **V31.1 tests:** None run. This milestone stopped at the data gate and made documentation-only changes; replay, cost, and performance tests would not establish the missing provenance evidence and would be downstream of the required stop condition.
- **Structural verification command:** Read-only Python chunk scan of `data/raw/btcusd_1-min_data.csv`; output recorded in the data audit. It is a dataset integrity check, not a unit-test suite.
- **Tracked-document whitespace check:** Targeted `git diff --check` completed without whitespace errors in tracked changes to `CHANGES.md` and `research/protocol_v1_2_proposal.md`. Git emitted a line-ending notice that `CHANGES.md` LF may be converted to CRLF; no content correction was needed. The new untracked Markdown files were not covered by this Git check.
- No V31.0 test result is represented as V31.1 validation. No strategy replay, tournament, live endpoint, or collector test was run.

## 7. Independent red-team findings

An independent, read-only code-review agent reviewed the initial V31.1 audit, report, and protocol matrix. **Result: no material findings in that draft.** It confirmed that the gates, blocked decision, and human-approval boundary were consistent and that evidence claims were qualified. The review did not edit files, run tests, or touch the collector or protected records. Subsequent factual updates were verified directly; the final integrity recheck then identified that the recorded initial entry-ledger digest was malformed, so Gate E is now explicitly blocked pending baseline-hash reconciliation.

Known risks retained without implementation changes:

1. Conflicting historical declarations could cause an operator to treat an unverified time or rights contract as accepted.
2. The Coinbase adapter's bucket-start timestamp can be mistaken for bar availability.
3. Existing replay and holdout inconsistencies can contaminate results if a tournament is run prematurely.
4. Assumed cost parameters and hypothetical perpetual funding can be misrepresented as historical executable costs.
5. Retrospective results cannot substitute for prospective confirmatory evidence.

## 8. Gate status

| Gate | Status | Evidence / reason |
|---|---|---|
| A — Data | **BLOCKED** | No candidate has reconciled identity, source timestamp/availability, permitted-use, and intended path granularity. |
| B — Replay | **BLOCKED / NOT RUN** | Data gate failed; known contract, path-completeness, common-holdout, and determinism issues remain. No performance replay run. |
| C — Economics | **BLOCKED / NOT RUN** | Cost methods disagree; historical funding, execution assumptions, and instrument mapping are unverified. No tuning or implementation change. |
| D — Governance | **PROPOSAL ONLY — HUMAN APPROVAL REQUIRED** | Separate V1.2 decision matrix provided; no confirmatory threshold or automated gate approved. |
| E — Integrity | **BLOCKED — ENTRY LEDGER BASELINE HASH UNVERIFIABLE** | Shadow ledger hash/count matches. Entry ledger still has five lines and current bytes normalize to the committed HEAD content, but the recorded initial digest is only 62 hex characters and cannot be compared as SHA-256. No ledger writes were made. Branch/HEAD are unchanged; final Git status contains 56 paths versus the 53-path initial inventory, exactly the three V31.1-created files added; existing dirty state was preserved. |

## 9. Required next step and governed decisions

**Next step:** recover the initial entry-ledger hash from a trustworthy baseline record (do not guess or modify the ledger), then resolve Gate A for one explicitly named dataset using primary evidence for timestamp/availability and permitted use; reconcile the Bitstamp approval/provenance records without rewriting old findings. If no candidate clears, remain blocked. Only after integrity and Gate A are clear should a separately reviewed replay contract and cost protocol be implemented and tested.

| Governed decision | V31.1 |
|---|---|
| Research experiment | `INCONCLUSIVE` — no accepted input; no tournament or strategy result. |
| Prospective evidence | `NOT_STARTED` for confirmatory entry outcomes; no collector action taken. |
| Model authorization | `OFFLINE_RESEARCH_ONLY` |
| Live trading | `DISABLED` |

This report makes no claim of profitability, calibrated entry probability, optimal TP/SL, live fill quality, or directional accuracy.
