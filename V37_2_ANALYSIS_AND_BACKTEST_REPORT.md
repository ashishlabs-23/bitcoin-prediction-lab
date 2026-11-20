# BTCognitive V37.2 — Analysis and Backtest Report

**Assessment date:** 2026-11-04  
**Mode:** Static research audit only; no data replay or model execution  
**Backtest status:** `INSUFFICIENT_DATA / HISTORICAL_RESEARCH_INCOMPLETE`

## Decision

No historical backtest was run. The available BTC/USD one-minute CSV remains unverified for original source authenticity, candle timestamp role, and historical availability. The existing holdout custody is also unverifiable, and the resolver's frozen execution contract has unresolved semantics. Consequently, this report gives no historical strategy or model performance metrics.

No historical OHLCV rows, protected holdout observations, or prospective ledger observations were accessed. The existing `research/entry_tp_sl/run_full_research_pipeline.py` was not executed: static inspection shows it reads the unverified CSV and writes research outputs, labels, ledgers, and custody/readiness artifacts.

## Pipeline map and lifecycle status

| Stage | Existing implementation | Status distinction and limitation |
|---|---|---|
| Data input | `research/entry_tp_sl/run_full_research_pipeline.py::run` reads `data/raw/btcusd_1-min_data.csv`. | Implemented; source/timestamp provenance is `UNVERIFIED`; not admissible for historical validation. |
| 15-minute aggregation and features | `run_full_research_pipeline.py` resamples the 1-minute input and `pit_features.py` computes rolling ATR, realized/Parkinson volatility, returns, RSI, volume ratio, SMA distance, and UTC-time features. | Implemented; no execution in this milestone. Resampling does not explicitly declare `closed`/`label`; feature code does not establish historical availability time or closed-candle status. |
| Candidate setups | `setup_detector.py` implements A1 sweep/reclaim and A2 range/reclaim; `detector_spec.py` declares a two-bar A1 reclaim window. | Implemented; not executed here. A1 currently detects sweep/reclaim on the same bar and does not apply the configured delayed window. |
| Entry contract and barriers | `triple_barrier.py::build_trade_contract` constructs entry and TP/SL barriers; `TripleBarrierEngine.resolve` resolves path bars; `reference_resolver.py` provides a reference implementation. | Implemented and covered by deterministic tests, but not fully contract-conformant/admissible for real outcomes. Timestamp alignment, entry-gap rule, incomplete horizon, opening-gap precedence, and cost semantics require owner decisions. |
| Feature/runtime integrations | `engine/trade_outcome_evaluator.py`, `engine/barrier_resolver.py`, and `engine/smart_entry_pipeline.py` are separate application paths. The evaluator fails closed when probabilities are unavailable. | Implemented paths are not interchangeable with the frozen `research/entry_tp_sl` research pipeline. No runtime execution or predictive validation was performed. |
| Baselines/classifiers | `baselines.py` includes random/directional/structural/trend baselines and logistic/LightGBM B4 variants. | Code exists; historical trial/report claims are unreconciled and not reproduced. No model was trained. |
| Walk-forward/statistical helpers | `walk_forward_engine.py` contains resampling/PBO-style helpers. | Helpers exist, but audit evidence identifies differences from the declared bootstrap/PBO protocols. The main research runner does not implement the declared purge/embargo split. No statistical result is accepted here. |
| Registry/forecasting | `models/authoritative_model_registry.py` separates volatility, directional research, price forecasting, and production authorization. HAR is a volatility model. | Registry and forecast modules are separate from this entry/exit backtest. No HAR forecast is attributed directional or trade performance. |
| Strategy tournament | `research/v12_strategy_tournament_engine.py` is another data and cost/simulation path. | Not equivalent to the Entry/TP/SL research design; no tournament or historical run was performed. |

Implemented, executed, tested, and statistically validated are distinct statuses. This audit confirms source presence, not successful runtime execution. Prior test and trial records are historical claims; they are not current validation.

## Point-in-time, split, and outcome risks

- **Causality:** Rolling features are backward-looking in form, but the feature builder does not by itself enforce an `available_time <= decision_time` cutoff. Unverified timestamp conventions prevent certifying point-in-time alignment.
- **Decision/fill/path alignment:** The runner selects a 1-minute row at `t0 + 60s`, uses its Open as fill input, and begins the path on subsequent rows. With the local contract's interval-close timestamp declaration, the mapping of that row's physical open to the execution instant is unresolved.
- **Missing fill and incomplete horizons:** The runner skips a setup if the exact fill timestamp is absent. Resolver behavior allows some short/no-touch paths to resolve near the full horizon; exact timeout endpoint versus observed-bar count and missing-bar tolerance need owner resolution.
- **A1 confirmation:** Current detection is same-bar; the specification's two-bar confirmation window is not implemented.
- **Entry gap and costs:** No entry-gap cancellation check is evident in the runner. Entry slippage is embedded in the research contract's entry-price construction, while the resolver also deducts aggregate round-trip cost including entry slippage. Whether this is intended is unresolved.
- **Barrier ambiguity:** Frozen rules specify conservative stop-first for unobservable same-bar dual touches, but opening-gap precedence/price representation in mixed gap-and-dual-touch bars is not fully settled.
- **Overlap and split integrity:** The pipeline applies a one-open-position filter using primary-pair exits, but inspected audit evidence says the full pipeline does not implement declared purging/24-hour embargo. Overlapping outcome horizons can therefore cross split boundaries unless corrected and verified.
- **Holdout:** The pipeline resolves outcomes before the research/holdout partition, while the holdout custody manifest is not independent access-control evidence. Do not tune against or claim confirmatory results from that cohort.
- **Historical claims:** Counts, trial IDs, and performance claims in existing reports remain unreconciled. No metrics were recalculated.

## Data admissibility and backtest decision

| Question | Decision |
|---|---|
| Is the minute CSV admissible for historical outcome-model evaluation? | **No.** `UNVERIFIED` provenance and timestamp semantics. |
| Is the existing holdout admissible for confirmatory claims? | **No.** Custody is `UNVERIFIABLE`. |
| Can Coinbase and Bitstamp history be joined as one series? | **No.** Separate venues, resolutions, timestamp contracts, and acquisition claims; no silent stitching. |
| Were any backtest metrics produced? | **No.** No historical replay, training, tuning, or test-set evaluation was run. |
| Can mechanics be tested without market evidence? | **Yes, as `PIPELINE_TEST_ONLY`**, using synthetic deterministic fixtures that are explicitly labelled non-market data. |

Required before a defensible historical evaluation: authenticated acquisition/provenance evidence or a replacement dataset with explicit instrument, UTC timestamp role, candle completion and availability semantics; frozen decisions for entry/path/gap/cost/timeout/A1 behavior; independent holdout custody or a newly governed untouched evaluation cohort; and a predeclared chronological split with purging/embargo, overlap accounting, costs, baselines, and uncertainty estimates.

## Exact unresolved owner questions

1. What source record authenticates the 1-minute dataset and what does each timestamp represent physically?
2. Which 1-minute bar is eligible for the fill and which subsequent intervals form the outcome path?
3. What is the 2% entry-gap reference, direction, boundary, and cancellation precedence?
4. How are opening gaps and dual-touch bars ordered and priced?
5. Is the horizon elapsed time or observed bars, what internal gaps are allowed, and how is an absent fill recorded?
6. Are entry/exit fees, spread, and slippage embedded in prices or deducted component-wise, and is the current apparent duplicate entry-slippage treatment intentional?
7. Does A1 allow delayed reclaim, what invalidates a pending sweep, and when does the signal timestamp begin?
8. What independent custody/access evidence establishes that the historic holdout remained untouched?
9. What frozen purge/embargo and effective-sample-size protocol governs future evaluations?

## Evidence boundary

This report is static inspection of source, tests, manifests, registry, and prior audit reports. No tests, model training, replay, external data request, protected observation access, calibration, or promotion occurred. The one-time Bitstamp market-data request was not performed because the official current terms could not be retrieved and permission therefore remained unclear.

### Research release states

- **Backtest:** `INSUFFICIENT_DATA / HISTORICAL_RESEARCH_INCOMPLETE`
- **Research validation:** `RESEARCH_VALIDATION_BLOCKED`
- **Prospective evidence:** `NOT_STARTED`
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`
- **Live trading:** `DISABLED`
