# V36.3A — Agent C: Holdout and Statistical Claims Findings

## Custody decision

**`UNVERIFIABLE`**

`holdout_custody_manifest.json` declares `SEALED_UNTOUCHED` for 2025-10-08 through 2026-10-07, with 2,662 trades and a seal time of 2026-10-07 17:03:59Z. It contains no access logs, separate immutable holdout object, or independent custody record. `run_full_research_pipeline.py::run` generates outcome records before it partitions `executed_trades` into `research_trades` and `holdout_trades`; it then writes the custody manifest. This means the code is not an isolation boundary. It does not by itself prove a holdout observation was used for model selection, so this audit does not claim that access history is known or that a specific holdout result was used.

The pilot manifest says labels were generated at 16:45Z, before the holdout seal at 17:03:59Z, and the feasibility report says the pilot was sampled across the 14.7-year timeline. Whether that sample includes holdout-period outcomes is unresolved. The pilot-label sample and protected holdout observations were not inspected.

## Claims reconciliation matrix

| Historical claim | Classification | Evidence and reconciliation | Confidence |
|---|---|---|---|
| Dataset digest and 500 pilot count | `SUPPORTED_BUT_INCOMPLETE` | `data_intake_manifest.json` declares the dataset SHA and 7,766,111 rows. `pilot_labels_manifest.json` records the same dataset SHA, `row_count=500`, outcomes 196 TP_FIRST / 283 SL_FIRST / 21 TIMEOUT, collision metadata 3, and terminal UNRESOLVED count 0. Sample contents were not inspected; aggregate provenance and uniqueness are not independently reproduced. | High for manifest fields; low for underlying labels. |
| 510,989 decisions / 510,973 eligible full paths | `SUPPORTED_BUT_INCOMPLETE` | `feasibility_audit.md` states these as raw-data feasibility counts, plus theoretical capacities. They are not observed model trades or an evaluation denominator. | High for claim classification. |
| 3,842 sequential opportunities versus 20,244 evaluation trades | `CONFLICTING` | `final_research_report.md:18-19` places both in the same one-position study without defining populations. Its generator hard-codes “3,842” but interpolates `n_eval` for 20,244. `trial_ledger.jsonl` reports B3 count 20,244, but does not supply distinct opportunity IDs. Do not select either figure as corrected. | High. |
| Duplicate trial IDs and changed metrics | `CONFLICTING` | Ledger has 17 records and 9 distinct IDs. B4-lite changes 216 / -0.2357R to 2,916 / -0.4673R; B4 BASE/CONSERVATIVE each change 0 count / 0 mean to 1,553 / -0.5678R and -1.0954R. B0/B3 IDs repeat with different entry hashes. Preregistration §AC requires each variation to be logged, but no amendments/unique run identities explain repetitions. | High. |
| B4 positive expectancy under low friction | `CONFLICTING` | `final_research_report.md` table gives B4 BASE -0.5678R and CONSERVATIVE -1.0954R, while its narrative says “modest positive expectancy under low friction.” The promotion decision claims +0.01R to -0.04R. Ledger’s later B4 rows match the negative table values, but conflicting ledger versions remain. | High. |
| Gross/net accounting and costs | `SUPPORTED_BUT_INCOMPLETE` | Preregistration specifies BASE 35 bps, CONSERVATIVE 65 bps, and net R as gross less normalized cost. Reports/ledger label mean net R, but provide no gross-to-net bridge or per-trade cost record; V36.3 resolver review also identifies potential double entry-slippage treatment. | High for frozen cost definition; reported result reconciliation incomplete. |
| Train/evaluation/calibration/holdout separation | `CONFLICTING` | Ledger uses coarse `train_window=2012-2021`, `eval_window=2021-2025`. Runner is one positional split of pre-holdout data, not a fold loop; it lacks the preregistered 4h purge and 24h embargo; no separate calibration partition is recorded. Outcome labels are computed before date partitioning. | High. |
| Prospective evidence exists | `UNVERIFIABLE` | Prospective readiness report gives prospective collection instructions and `N>=100` criterion, not collected observations or a ledger count. It is not evidence of prospective validation. | High. |
| Promotion decision `COST_ERASED` and statistical claims | `CONFLICTING` | Promotion rationale’s +0.01R to -0.04R range conflicts with final report and ledger B4 values. Final report claims Holm/DSR/PBO, but runner resamples 2,000 versus preregistered 10,000; `stationary_block_bootstrap_ci` uses fixed-size circular blocks and PBO code is a two-half proxy, not the registered CSCV procedure. | High for conflict; no replacement inference computed. |
| Historical tests passed on exact source | `UNVERIFIABLE` | 6B manifest contains PASS strings but no command/node logs; its recorded commit does not contain source paths. Current source contents are recoverable, but test execution/source binding is not proved by available records. | High. |

## Facts, inference, and unknowns

- **Observed facts:** manifests and reports contain the values above; the trial ledger repeats IDs; the runner partitions after constructing labeled records and writes the custody manifest; pilot manifest precedes the stated seal time.
- **Inference:** the `SEALED_UNTOUCHED` string is not a custody control; report and ledger cannot establish a unique evaluation cohort.
- **Unresolved:** whether the pilot sampled holdout dates, whether any person/model-selection process inspected those labels, exact run identities for repeated trial IDs, and exact unique-trade denominator.

## Recommendation

Do not use the historical holdout for confirmatory model claims absent independent custody/access logs and a demonstrated isolated object. Preserve all old reports and ledger events; classify disputed counts/results as conflicting rather than selecting a corrected value. Before another evaluation, use a unique run ID bound to source/code/config/environment, define distinct candidates versus labels versus executed non-overlapping trades, and record calibration/fold/holdout assignments before labels are exposed. A future confirmatory set must be independently held out or prospective; the report’s readiness criteria do not prove that such evidence exists.

## Inspected files

`research/entry_tp_sl/holdout_custody_manifest.json`; `pilot_labels/pilot_labels_manifest.json` (manifest only; sample file not read); `trial_ledger.jsonl`; `PREREGISTRATION_v1.md`; `feasibility_audit.md`; `final_research_report.md`; `PROMOTION_DECISION.md`; `prospective_readiness_report.md`; `run_full_research_pipeline.py`; `6B_implementation_manifest.json`; `contract_freeze_manifest.json`; `data_intake_manifest.json`; `g0_closure_report.md`; `setup_registration.md`; `decision_contract.json`; `entry_execution_contract.json`; `outcome_accounting_contract.json`.
