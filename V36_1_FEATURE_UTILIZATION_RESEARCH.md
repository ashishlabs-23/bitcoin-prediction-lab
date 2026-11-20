# BTCognitive V36.1 — Feature Utilization Research

## Status and research boundary

This is a design-level assessment based on source contracts and existing local research documents. No feature combinations were fitted, scored, tested, or benchmarked in V36.1. A route, checkpoint, test file, or successful import is not evidence that a feature improves predictions. The Standard HAR forecast accuracy remains `NOT_ESTABLISHED`; prospective evidence is not substituted with historical replay.

The high-level separation follows common econometric practice: HAR models volatility rather than return direction (Corsi, 2009); volatility forecast comparisons must use loss functions appropriate to variance proxies such as QLIKE (Patton, 2011; Puke & Schweikert, 2026); forecast comparisons require dependence-aware inference (Diebold & Mariano, 1995; Harvey, Leybourne & Newbold, 1997); forecast evaluation and window design must respect chronology (Tashman, 2000); and model selection among many challengers must account for data snooping (Hansen & Lunde, 2005; Hansen, Lunde & Nason, 2011). The local [V35_2 volatility research report](./V35_2_VOLATILITY_MODEL_RESEARCH.md) discusses loss-coherent QLIKE estimation and records prior historical results; those results are retrospective and were not independently reproduced or revalidated in V36.1. These citations motivate protocol design only; no external literature review was run for V36.1.

## Use by analytical purpose

| Purpose | Existing capability candidates | Appropriate role | Must not be used as |
|---|---|---|---|
| Market-state estimation | Point-in-time OHLCV features; TwoSpeedMarketState; MarketRegimeDetector; semivariance; actual funding/open interest where timestamped | Describe state and condition other estimates; report unavailable fields explicitly | Proof of a tradable regime, calibrated posterior, or return prediction |
| Directional setup generation | Frozen `StructuralSetupDetector` A1/A2; separately governed hourly `StrategySignalEngine` candidates | Generate a deterministic candidate set and side using only completed bars | A probability of TP-first or a production signal |
| Volatility forecasting | Standard HAR when its exact artifact/lineage is recovered; HAR-RS-DOW as unpromoted challenger; semivariance; separately specified 15m forecast | Forecast an explicit realized-variance target and evaluate with variance-appropriate loss | Direction forecast, trade return, or profitability claim |
| Market microstructure | L2 imbalance/depth/spread/OFI/CVD from timestamped event feeds | Execution diagnostics or candidate timing only when venue and event coverage are adequate | OHLCV-derived synthetic order flow or a currently available input |
| Trade-risk calculation | Frozen barrier/cost contracts; risk budget; independent cost scenarios; uncertainty/data-quality checks | Reject infeasible or unsafe candidates and calculate scenario-specific net R | A forecast edge or a substitute for observed fills |
| Outcome-probability modelling | Candidate-level TP_FIRST/SL_FIRST/TIMEOUT meta-model (not yet a validated 3-class model) | Estimate the outcome distribution conditional on a named candidate and frozen contract, after sufficient evidence | Generic BTC up/down probability or volatility-model output |
| Model/data governance | Artifact registry; provenance; FeatureStore; forecast observatory; immutable trial/evidence contracts | Enforce identities, time cutoffs, maturity, and append-only evidence boundaries | A validation result merely because a registry/status endpoint exists |

## Dependency-aware execution plan

1. **Acquire or select a governed source.** Verify instrument, source, timeframe, event and availability timestamps, closed-bar status, hash, and gaps before calculation. The V36.1 replay path is offline-only and uses the existing local snapshot.
2. **Normalize and validate.** Reuse the normalized-candle contract; reject duplicates, nonfinite values, invalid OHLC geometry, gaps, and forming candles. Do not repair by synthesizing observations.
3. **Construct only eligible PIT features.** Each feature declares source fields, cadence, lookback, availability rule, units, missing behavior, and whether it is fit only on training data. Separate feature and target builders.
4. **Estimate state and forecasts.** Execute only services with available source columns and explicit horizon. A missing auxiliary feature yields `DATA_UNAVAILABLE`; no neutral constant is allowed to masquerade as an observation.
5. **Generate candidates, if in scope.** One frozen setup detector owns candidate side and timestamps. Do not mix the separate hourly strategy suite without a documented cadence/contract bridge.
6. **Apply deterministic risk and data gates.** Keep costs, fees, spread, slippage, horizon, overlap, and collision semantics frozen. Missing cost evidence can be a sensitivity scenario, not an observed market quote.
7. **Evaluate probability separately.** A classifier is conditional on a candidate and the frozen TP/SL/timeout definition; do not use HAR, regime class, or directional output as a probability of success.
8. **Serialize provenance.** Return source hash, snapshot status, `as_of_timestamp`, horizon, model identity, feature availability, explicit status, and abstention reason. Frontend rendering must preserve these fields and must not manufacture defaults.
9. **Persist nothing in historical replay.** No call may write to the prospective ledger, market-memory DB, FeatureStore, observatory, risk budget, or experiment/trial ledgers.

## Feature inclusion decisions

- **Potentially eligible for a later baseline:** simple, causal OHLCV-only state/volatility features at a cadence supported by verified source data. Eligibility is not a claim of predictive contribution.
- **Candidate generation only:** A1/A2 structural setup and explicitly governed hourly candidate rules. Preserve one setup's origin, side, fill convention, and abstention reasons.
- **Risk only:** barrier geometry, cost scenarios, data-quality gates, drawdown and position budget. These do not add alpha by construction.
- **Conditional diagnostics:** regime labels and semivariance. Test incremental value over the same baseline; do not select regimes based on test outcomes.
- **Unavailable until acquired and permissioned:** L2/order-book events, trades/matches, funding, open interest, liquidations, and any source-restricted provider inputs. Hourly OHLCV cannot substitute for them.
- **Exclude from current probability model:** unvalidated range multipliers, uncertainty scores without calibration artifacts, future targets, same-bar information, current system time, and any fields whose point-in-time availability is unknown.
- **Do not combine blindly:** 1m, 15m, hourly, 24h, and 7d features/targets have distinct sampling and maturity contracts. Only merge by explicit timestamp and availability semantics; do not treat step counts as interchangeable durations.

## Reproducible research hypotheses (not results)

H1: adding causal trend/momentum inputs to the frozen candidate baseline reduces out-of-sample candidate-level log loss or improves net utility at frozen costs.

H2: adding a volatility forecast improves an explicitly defined risk/size or excursion target, evaluated separately from direction and at matching horizons.

H3: regime features add incremental value beyond the same baseline and covariates, with inference clustered/purged by overlapping outcomes.

H4: true timestamped microstructure data improves entry timing or execution diagnostics beyond candle-only information under the same venue, event coverage, and latency assumptions.

All hypotheses are untested. A feature is retained only after the preregistered ablation protocol is met on non-final chronological development folds; final and prospective evidence remain untouched.

## Decision

No evidence currently supports a unified predictive feature bundle. Keep feature assembly modular and dependency-aware. The eventual system should abstain (`NO_TRADE`) when candidate, source, model, cost, horizon, or risk evidence is unavailable or fails its frozen gate. It must not promise a winning trade.
