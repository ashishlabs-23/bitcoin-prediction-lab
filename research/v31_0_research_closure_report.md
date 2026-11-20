# BTCognitive V31.0 — Research Closure and Entry Validation

**Review date:** 2026-10-23
**Repository HEAD inspected:** `24092a118bb4285cb2675cbc02694d34800d92d5`
**Branch:** `main` (no branch created)
**Governance:** `OFFLINE_RESEARCH_ONLY`; order execution and live trading remain disabled
**Scope clarification:** “Go live” is interpreted as a possible future read-only prediction/monitoring surface. This V31.0 review does not enable that surface or any order execution.

## 1. Executive decision

### `RESEARCH BLOCKED — DATA OR METHODOLOGY DEFECT`

The repository contains substantial strategy, cost, barrier, tournament, meta-labeling, and prospective-shadow components. The presence of these components and passing tests does not establish a reproducible historical edge. V31.0 historical strategy results could not be independently reproduced or accepted because:

1. The current hourly tournament input is identified as Binance BTCUSDT in the ingestion code but is treated as Coinbase BTC-USD by the V12 tournament. Its current SHA-256 differs from the hash in the V12 manifest.
2. The V12 runner does not consistently constrain every candidate to its stated holdout; the 4-hour candidate path uses the full 4-hour dataframe. Its split is recalculated from the current input and the report includes a runtime timestamp, so this is not a frozen deterministic replay contract.
3. The local Bitstamp-derived minute snapshot is present and structurally sound, but the repository contains conflicting instrument, timestamp-semantics, source-rights, and availability declarations. It cannot be silently substituted for Coinbase or assumed to represent executable fills.
4. Historical entry-lab reports conflict internally on the number of one-position trades and on net expectancy. The values below are therefore inherited claims, not reproduced results.
5. V1.1 does not define a valid trade-level confirmatory sample gate. The V30.9 audit correctly rejects `100 × E[L]=5 = 500 trades`, but its suggested 100-trade interpretation and illustrative effective sample size are not themselves a power or precision justification.

No strategy is recommended as profitable, deployment-ready, or “accurate” in the sense of guaranteed entries or barriers. An accurate TP/SL claim is not supportable from OHLC backtests alone: intrabar order, spread, queue position, slippage, fills, and adverse selection are not observed in the available data.

### Governed decisions

| Decision | V31.0 result |
|---|---|
| Research experiment | `INCONCLUSIVE` — historical strategy claims were not reproduced under a single verified instrument/data/holdout contract. |
| Overall V31.0 decision | `RESEARCH BLOCKED — DATA OR METHODOLOGY DEFECT` |
| Prospective evidence | `NOT_STARTED` for confirmatory trade-outcome evidence: the shadow ledger has 0 candidates and 0 resolved outcomes. The collector’s present running state could not be verified; do not infer active collection from stale telemetry. |
| Model authorization | `OFFLINE_RESEARCH_ONLY` |
| Live trading | `DISABLED` |
| Future read-only live predictions | Not enabled or validated by this review; may be considered separately without adding execution capability. |

## 2. Evidence classification and scope

- **Reproduced here:** current Git identity/status; read-only ledger counts and hashes; local dataset byte/hash/shape/structural checks; targeted regression tests.
- **Verified by source inspection:** which implementation surfaces and candidate strategies exist, their stated assumptions, and selected inconsistencies between source, manifests, and reports.
- **Inherited, not reproduced:** historical performance tables, candidate trade counts, bootstrap intervals, DSR/PBO values, and prior live-feed observations.
- **Not claimed:** profitability, live fill quality, exact executable entries, an optimal TP/SL, directional accuracy, or prospective confirmation.

The frozen strategy and Protocol V1.1 were not modified. The report-generation and dataset-audit commands were read-only; no shadow-feed command was run, and no collector was started, stopped, restarted, or reconfigured. Test processes were also run, so their indirect side effects cannot be ruled out. On final recheck, the specified entry and shadow ledgers retained their original hashes. A separate forecast ledger and several unrelated tracked research/result artifacts changed during this session window while two pre-existing, full `pytest -q` processes were active. Their origin cannot be attributed confidently; they were left untouched.

## 3. Verified capability matrix

| Area | Current state | What the repository supports | Limitation relevant to closure |
|---|---|---|---|
| Strategy selection | Partial | Five named candidates, side/rank logic, eligibility checks, and abstention exist in `engine/strategy_selection.py`. | Its selection evidence is not a verified historical tournament: some sample counts are constants and residual series are seeded synthetic AR(1), not observed candidate outcomes. |
| Probabilistic entry | Partial | Features, candidate probabilities, and a cost-aware gate exist in `engine/probabilistic_entry_engine.py`. | Fixed weights/probability components do not establish empirically fitted, calibrated outcome probabilities. Do not label a displayed probability “validated” absent fit/calibration provenance. |
| Cost accounting | Implemented, with interface risk | Itemized fee, spread, slippage, and funding methods exist in `engine/execution_cost_model.py`. | Legacy `calculate_roundtrip_cost` and class `calculate_round_trip_cost` differ in fee treatment; every caller/scenario needs a traced, tested path before economics are trusted. |
| Entry contracts/barriers | Implemented | Immutable candidate/outcome contracts, geometry checks, gap handling, conservative same-bar collision, timeout and excursion tracking exist in `engine/entry_contracts.py` and `engine/barrier_resolver.py`. | Contract text says features precede fill, while timestamp validation permits fill time equal to decision time; timestamps are compared as strings. The resolver's assumed fill/bar timing must be made explicit for each dataset cadence. |
| Decision envelope | Implemented with audit caveat | Hash-chained decisions, replay, integrity checks, and null semantics are present in `engine/decision_envelope.py`. | Broad exception handling on some read paths can conceal malformed or inaccessible records; it should not turn invalid evidence into a normal-looking empty result. |
| Stationary bootstrap | Utility exists | `engine/stationary_bootstrap.py` implements geometric stationary resampling and confidence-interval utilities. | A resampling routine is not a sample-size rule or a confirmatory gate. Segment identity, dependence assumptions, block-length choice, and gate eligibility need a governed definition. |
| Strategy tournament | Research tooling exists | V12 defines five strategy candidates and baseline policies, and has tournament routes/tests. | Current input provenance, holdout use, output determinism, and manifest freshness prevent accepting the existing metrics as a V31 reproduction. |
| Meta-labeling | Separate capability | Logistic/meta-labeling and other classifier components are in the repository. | Not wired as a verified, nested walk-forward comparison within the current V12 tournament. Prior reported net results are negative and remain inherited. |
| Prospective shadow | Plumbing exists; evidence absent | Feed/collector, append-only ledger, operational status, and focused tests are present. | Ledger is empty (0 candidate/outcome records); the current process state is unverified. Test fixtures are not real prospective outcomes. |

### Existing V12 candidates and comparison policies

The V12 engine identifies:

- `REGIME_ADAPTIVE_ROUTER`
- `MTF_MOMENTUM_TREND`
- `VOL_COMPRESSION_BREAKOUT`
- `HTF_RANGE_EXPANSION_BREAKOUT`
- `SHORT_HORIZON_MEAN_REVERSION`

Named comparison policies include no-trade/abstention, buy-and-hold, volatility-targeted bull exposure, and matched-random entry. This is useful prior art; it does not establish that the requested five archetypes were compared under one frozen, common, valid holdout. The V12 labels do not map one-to-one onto all requested archetypes: pullback and liquidity-sweep/Turtle-Soup need explicit definitions or verified reuse before a tournament is preregistered.

## 4. Historical data and replay reproducibility

### Local artifacts checked

| Dataset | Observed local identity | What can be said | What cannot be assumed |
|---|---|---|---|
| `data/raw/btcusd_1-min_data.csv` | 393,952,273 bytes; SHA-256 `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`; 7,766,111 rows. | A read-only chunked scan found 0 null cells, 0 invalid OHLCV rows, 0 duplicate/nonpositive timestamps, and all timestamp steps exactly 60 seconds. The hash matches the archived candidate snapshot claim. | This does not prove timestamp availability/close semantics, exchange provenance, rights clearance, or executable Bitstamp fills. Repository documentation conflicts: one intake record says approval/resolution, while the candidate template still identifies unresolved timestamp and rights review. |
| `data/raw/ohlcv.parquet` | SHA-256 `838e2b889729be163672c06481a475dc7989d15ba1f3dabbb4f9c54ad85a4e16`; the prior V12 manifest records 41,273 rows and a different hash. | Ingestion source identifies Binance BTCUSDT; the separate tournament code labels the data Coinbase BTC-USD. | It is not a valid Coinbase BTC-USD fill history. Current file and stale manifest cannot be treated as the same frozen replay input. |
| `data/raw/coinbase_15m.parquet` | 449,898 bytes; SHA-256 `89c9017256a47dc41e66615073c0890a66ea66b35dc505e1b14abe4b8ec463c7`; manifest records 8,710 bars from 2026-07-24 16:45 UTC through 2026-10-23 10:00 UTC. | A Coinbase BTC-USD dataset with a documented manifest is available for a limited recent-period study. | Its short span cannot validate long-regime stability or reproduce a multi-year strategy tournament. |
| `data/raw/binance_funding_2022_2026.parquet` | SHA-256 `e90282de4f78ebde4b0e253cd71e50233d965062defa9f1b81be5b87da094436`. | A funding file exists. | Existence alone is not a point-in-time join or proof that historical funding was included in the tournament costs. |

### Replay acceptance

No V31 historical replay was run. The existing tournament runner is not a suitable replay engine without isolation and correction: the holdout is not uniformly applied, the split is recomputed from the present dataframe, and instrument labels do not match the source. Running it and reporting its output as a reproduction would violate the brief’s source/instrument and holdout requirements.

A valid future replay needs an immutable input/config hash; explicit venue/product identity; timestamp availability semantics; completed-candle rules; deterministic chronological decisions; train-only preprocessing; next-available fill timing; gap/missing-bar policy; conservative intrabar ambiguity; and recorded candidate/abstention/fill/cost/outcome/reason fields. Repeated-run equality and tests for leakage, resampling boundaries, duplicates, gaps, and restart-independent output are acceptance requirements. Simulated results must remain outside both prospective ledgers.

## 5. Tournament, baselines, and economics

The repository provides strategy candidates and comparison policies, but no V31 result table is accepted here. Prior V12, V18, V28, and Entry Lab reports/manifests are not current reproductions: input hashes and/or end dates differ, and the V12 instrument identity/holdout issues above apply.

Specific inherited Entry Lab conflicts requiring reconciliation:

- `research/entry_tp_sl/final_research_report.md` reports 3,842 sequential one-open-position opportunities but also a 20,244-trade unseen out-of-sample evaluation count. Those counts cannot both describe the same one-position, non-overlapping evaluation population as written.
- The same report's table gives B4 LightGBM mean net return `-0.5678R` under “BASE,” while its narrative describes modest positive low-friction expectancy.
- `research/entry_tp_sl/PROMOTION_DECISION.md` reports a different `+0.01R` to `-0.04R` range. None of these values was recomputed from the pipeline in this closure.

For completeness, the old Entry Lab table reports the following negative net-R figures. They are preserved here as **inherited report values only**; this review did not reproduce them:

| Prior policy/model | Reported \(N\) | Reported win rate | Reported mean net R |
|---|---:|---:|---:|
| Matched random | 10,105 | 25.7% | -1.2112R |
| Always long | 10,142 | 26.1% | -1.1900R |
| Always short | 10,102 | 25.7% | -1.2110R |
| Structural rule B3 | 20,244 | 25.9% | -1.2005R |
| B3 plus trend filter | 1,665 | 18.7% | -1.5708R |
| Logistic B4-lite | 2,916 | 46.9% | -0.4673R |
| LightGBM B4, “BASE” | 1,553 | 47.1% | -0.5678R |
| LightGBM B4, “CONSERVATIVE” | 1,553 | 25.2% | -1.0954R |

The V12 retail manifest separately reports all five candidate strategies as negative after costs; for `HTF_RANGE_EXPANSION_BREAKOUT`, it records 194 trades and `-57.4 bps` net expectancy. The no-trade policy is recorded as zero return/drawdown in the V12 test contract. These prior summaries cannot identify the current data bytes or remedy the holdout mismatch. The Entry Lab out-of-sample trade counts above also conflict with its own one-position count as noted above.

Cost scenarios are assumptions, not observed executions:

| Scenario | Reported assumption | V31.0 interpretation |
|---|---:|---|
| Coinbase retail spot | 87 bps round trip | Can be a declared sensitivity if the simulated instrument is Coinbase BTC-USD; not proof of historical realized spread/slippage. |
| Coinbase institutional spot | 18.6 bps | Sensitivity only; account eligibility and historical fee schedule need evidence. |
| Binance USDT perpetual | 15 bps, including a fixed 2 bps funding item in V12 | Not directly comparable to spot. Funding varies by time and instrument; a fixed charge is not a historical funding replay. |
| Adverse stress | 120 bps in V1.1 | A transparent stress assumption, not a measured fill rate or friction distribution. |

No local order-book history was identified. OHLC-derived spread/imbalance proxies are estimated signals, not observed quotes. Maker fills, queue priority, partial fills, missed fills, adverse selection, and realized spread cannot be claimed from this data. Venue comparisons must be separated by instrument and reported as scenario sensitivity, not ranked as interchangeable opportunities.

## 6. Meta-labeling and entry quality

The repository contains logistic/meta-labeling code, but the existing outcome summaries do not establish incremental net value for a V31 integrated pipeline. V28 reports a 46.9% logistic-filter win rate with mean net return `-0.4673R`, and other model summaries report negative net expectancy. These are **inherited values**, not independently reproduced in this review.

A valid next comparison must:

1. Include a transparent rule and regularized logistic baseline; add shallow boosted trees only if already installed and supported.
2. Build features strictly from data available at decision time; fit imputation, scaling, model selection, and probability calibration inside each chronological training fold.
3. Purge and embargo overlapping outcome windows; freeze the final holdout before model/configuration selection.
4. Evaluate target-first, stop-first, and timeout probabilities only where labels and censoring rules support them.
5. Report Brier score/reliability with uncertainty, coverage/abstention, net expectancy after scenario costs, drawdown, turnover, and incremental value versus both the frozen baseline and zero exposure.
6. Record every tried strategy/model/configuration; do not use win-rate thresholds as a substitute for economic value or uncertainty.

## 7. Statistical protocol findings and V1.2 proposal

### V30.9 findings reproduced by source/test audit

- The 100-clean-block rule originated in a forecast-evaluation context in which a block is associated with non-overlapping forecast origins/horizons; that does not automatically become 100 completed trades.
- V1.1 calls one candidate setup an observation but leaves the confirmatory “100 blocks” phrase undefined for variable-duration trade outcomes.
- \(E[L]=5\) is the stationary-bootstrap geometric resampling length parameter. It is not a factor converting 100 evidence units into 500 completed trades.
- In-position gating guarantees non-overlapping exposure intervals, not statistically independent outcomes. The V30.9 `N_eff` illustration plugs in an assumed autocorrelation; it does not estimate dependence from prospective returns or demonstrate power.
- The stationary-bootstrap utility implements a resampling method but does not implement the 100-unit gate.
- The cited DM-HLN code is designed for aligned forecast-loss comparisons. A trade-return gate requires a predeclared common estimand, matched sample, benchmark, horizon, loss/return sign, dependence estimator, and one-sided decision. Trade-matched excursion and calendar-time equity are different estimands.
- The V30.9 DM-HLN fixture checks a manually calculated correction rather than an end-to-end paired trade-loss procedure. The V30.9 drawdown fixture does not test a breach-triggered pause branch.

`research/protocol_v1_2_proposal.md` is provided for human review. It does not replace or amend frozen V1.1. In particular, it does **not** set 100 trades as sufficient; the evidence threshold remains unset pending a defensible precision/power analysis and frozen estimand.

DSR/PBO/CSCV should be used only after the full trial family and data-splitting structure are known and frozen. Their names or point estimates do not cure leakage, multiple undocumented trials, input mismatch, or an invalid holdout.

## 8. Independent red-team findings

| Severity | Finding | Consequence |
|---|---|---|
| Blocker | Binance BTCUSDT historical hourly input is labeled Coinbase BTC-USD in the V12 tournament. | Venue-specific costs/fills and reported baseline cannot be matched to the replay observations. |
| Blocker | Holdout is not applied to every V12 candidate; the 4-hour path evaluates the full frame. | Candidate comparisons and apparent out-of-sample results may be contaminated. |
| Blocker | V1.1’s “100 blocks” has no trade-specific unit or sample-size rationale; no automated gate exists. | Confirmatory status cannot be assigned. |
| High | Input hashes in previous manifests are stale against current files. | Prior metrics do not identify the current bytes used. |
| High | Entry Lab counts and net-expectancy narrative conflict. | Historical claims need pipeline-level reproduction and reconciliation, not averaging. |
| High | No order-book history; funding/fill assumptions are incomplete or fixed. | Execution economics and maker advantage are unverified. |
| Medium | Entry contract timing permits equal decision/fill timestamps despite strict causal wording; timestamp comparisons are lexical. | Potential boundary inconsistency if different timezone encodings or cadences are used. |
| Medium | Cost-model legacy and class methods differ on fee arithmetic. | Cost result depends on which method a caller invokes; audit caller paths before use. |
| Medium | Strategy-selection evidence includes formula-generated sample counts and synthetic residuals. | Do not present selector rankings as empirical evidence. |

### Read-only collection check

The status JSON reports last cycle `2026-10-23T13:13:46Z`, `HEALTHY`, and 0 candidates/outcomes. The lock file contains PID `31676` with the same acquisition time; that PID was not active when checked. Therefore the collector’s current running state **could not be verified**. The lock/status/ledgers were not changed, and no runner command was invoked.

## 9. Exact validation, repository state, and evidence hashes

### Tests executed

Focused research/contract suite:

```powershell
& 'c:\Projects\BTCognitive\BTCognitive\.venv_win\Scripts\pytest.exe' -q `
  'c:\Projects\BTCognitive\BTCognitive\tests\test_entry_contracts_and_resolver.py' `
  'c:\Projects\BTCognitive\BTCognitive\tests\test_prospective_shadow_collector.py' `
  'c:\Projects\BTCognitive\BTCognitive\tests\test_shadow_feed_runner.py' `
  'c:\Projects\BTCognitive\BTCognitive\tests\test_v30_6_operational_proof.py' `
  'c:\Projects\BTCognitive\BTCognitive\tests\test_v30_7_shadow_burnin.py' `
  'c:\Projects\BTCognitive\BTCognitive\tests\test_v30_8_collection_integrity.py' `
  'c:\Projects\BTCognitive\BTCognitive\tests\test_v30_9_statistical_gate_audit.py' `
  'c:\Projects\BTCognitive\BTCognitive\tests\entry_tp_sl'
```

**Result:** 147 passed in 15.79 seconds. This validates software fixtures and existing contract behavior; it does not validate a real-market outcome, strategy profitability, or prospective sample sufficiency. No full repository suite or historical V31 replay was run.

Prior tournament/meta-labeler regression:

```powershell
& 'c:\Projects\BTCognitive\BTCognitive\.venv_win\Scripts\pytest.exe' -q `
  'c:\Projects\BTCognitive\BTCognitive\tests\test_v12_strategy_tournament.py' `
  'c:\Projects\BTCognitive\BTCognitive\tests\test_meta_labeler.py'
```

**Result:** 12 passed in 211.54 seconds; one `StarletteDeprecationWarning` from the installed `starlette.testclient` integration with `httpx`. These tests also do not resolve the stale-input, venue, or holdout issues described above.

### Git and ledger state

- **Branch:** `main`
- **HEAD:** `24092a118bb4285cb2675cbc02694d34800d92d5`
- **Pre-report worktree:** 38 changed paths were already present (15 tracked modifications and 23 untracked files as reported by `git status`); preserved. Later snapshots showed 12 other tracked paths modified: `data/prospective_forecast_ledger.jsonl`, `experiments/results/multi_regime_validation_report.json`, `experiments/results/post_repair_milestone_5_lock.json`, `experiments/results/stage10_shadow_validation/shadow_prediction_ledger.jsonl`, `experiments/results/stage11_forward_validation/forward_prediction_ledger.jsonl`, `research/production_review_block_10.md`, `research/reports/post_repair_5_block_observed.md`, `research/reports/post_repair_baseline.md`, `research/reports/post_repair_restart_review.md`, `research/reports/pre_post_repair_comparison.md`, `results/mamba_trial_manifest.json`, and `results/model_change_request.json`. The earlier modification to `results/mamba_dataset_manifest.json` was no longer present at the later snapshot; its prior uncommitted contents were not captured and could not be reconstructed. Two other Python processes were running `pytest -q`, had started before the focused V31 tests, and remained active at the last status capture. The focused test sources do not directly name these artifacts, but concurrent activity prevents reliable attribution. No unrelated changes were reverted. The final captured status contained 52 changed paths. No branch, commit, push, deployment, or strategy configuration change was made.
- `data/prospective_entry_ledger.jsonl`: 5 lines; SHA-256 `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7ac4d7`.
- `data/prospective_shadow_v1.jsonl`: 0 lines; SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Counts and hashes were the same after the focused tests. No simulated records were written.

## 10. Next steps and go/no-go criteria

1. **Do not rank or promote a “top strategy” yet.** First freeze the venue/instrument-specific historical input and resolve its timestamp semantics, rights record, and manifest hash.
2. **Repair replay boundaries in a separate research-only change.** Require every candidate to use identical frozen train/validation/test windows and enforce the same no-lookahead and fill-time contracts. Add a reproducibility manifest and repeated-run checks.
3. **Reconcile legacy Entry Lab claims.** Re-run the original preregistered pipeline only after verifying it consumes the frozen data, candidate population, and costing rules; explain and correct count/metric contradictions in a dated addendum, never by overwriting prior reports.
4. **Review and approve Protocol V1.2.** Specify the primary estimand, evidence unit, precision/power basis, CI and interim-look policy, benchmark alignment, and eligible/excluded outcomes. Until then the confirmatory gate is blocked.
5. **Run the preregistered five-archetype tournament only after 1–4.** Include matched random, buy-and-hold, always-long/short where meaningful, and zero exposure; use identical supported regimes, report abstention/exposure, cost sensitivity, uncertainty, and all tested configurations.
6. **Add nested walk-forward meta-labeling only after candidate definitions and outcome labels freeze.** No final-holdout tuning; evaluate calibration and incremental net value, not win rate alone.
7. **Keep future “live” read-only.** A forecast UI may be considered as a distinct, non-executing feature after interface and monitoring requirements are reviewed. It must expose uncertainty, stale/missing data, abstention, model authorization, and provenance; it must not route orders or imply guaranteed outcomes.

### Go/no-go criteria

- **GO to historical comparison:** data identity/provenance/rights and timestamps reconciled; all strategies use the same frozen, causal holdout; costs are instrument-matched; deterministic replay passes boundary and repeat-run tests.
- **GO to confirmatory prospective evaluation:** human-approved V1.2 with an explicit evidence unit and defensible precision/power rule; prospective records are post-freeze and quality eligible; test code exercises the actual gate and interim stopping policy.
- **GO to read-only forecast surface:** separate acceptance review for stale-feed handling, calibrated uncertainty/abstention presentation, model registry authorization, and no execution paths.
- **NO-GO to strategy deployment or claims of profitable/accurate entries:** current V31.0 evidence does not support either.

## 11. References and relevance

- Corsi, F. (2009). “A Simple Approximate Long-Memory Model of Realized Volatility.” *Journal of Financial Econometrics*, 7(2), 174–196. DOI: `10.1093/jjfinec/nbp001`. Volatility modeling reference; not evidence for entry direction or profitability.
- Puke, M., & Schweikert, K. (2026). “Coherent Forecasting of Realized Volatility.” *Journal of Forecasting*, 45(4), 1714–1729. DOI: `10.1002/for.70114`. Relevant to coherent volatility-loss estimation; not an entry-strategy result.
- Diebold, F. X., & Mariano, R. S. (1995). “Comparing Predictive Accuracy.” *Journal of Business & Economic Statistics*, 13(3), 253–263. DOI: `10.1080/07350015.1995.10524599`.
- Harvey, D. I., Leybourne, S. J., & Newbold, P. (1997). “Testing the Equality of Prediction Mean Squared Errors.” *International Journal of Forecasting*, 13(2), 281–291. DOI: `10.1016/S0169-2070(96)00719-4`.
- Politis, D. N., & Romano, J. P. (1994). “The Stationary Bootstrap.” *Journal of the American Statistical Association*, 89(428), 1303–1313. DOI: `10.1080/01621459.1994.10476870`.
- Tashman, L. J. (2000). “Out-of-sample tests of forecasting accuracy: an analysis and review.” *International Journal of Forecasting*, 16(4), 437–450. DOI: `10.1016/S0169-2070(00)00065-0`.
- Hansen, P. R., Lunde, A., & Nason, J. M. (2011). “The Model Confidence Set.” *Econometrica*, 79(2), 453–497. DOI: `10.3982/ECTA5771`.
- Patton, A. J. (2011). “Volatility forecast comparison using imperfect volatility proxies.” *Journal of Econometrics*, 160(1), 246–256. DOI: `10.1016/j.jeconom.2010.03.034`.

These methods inform forecast evaluation and uncertainty procedures. They do not convert volatility forecasts into directional accuracy or a profitable trading strategy.
