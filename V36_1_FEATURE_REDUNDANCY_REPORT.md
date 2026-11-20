# BTCognitive V36.1 — Feature Redundancy and Compatibility

## Status

Static, qualitative redundancy analysis only. Correlations, conditional mutual information, ablations, and predictive contribution were not measured. No feature is removed or promoted by this report.

## Likely overlap and separation

| Feature families | Potential overlap | Required handling |
|---|---|---|
| Log-return lags, moving-average slopes, EMA ratios, trend filters, Donchian/trend candidates | Multiple encodings of trend/momentum; overlapping windows and same OHLCV source | Group into one preregistered trend/momentum ablation. Examine feature correlation and conditional permutation on training folds only. Avoid simultaneous feature selection and threshold tuning on final holdout. |
| HAR lagged realized variances, rolling volatility, 24h volatility, semivariance, ATR | All reflect range/volatility but target/proxy/cadence differs; semivariance adds sign-asymmetric components | Keep target definitions distinct. Compare within horizon. Do not count different transforms of the same return stream as independent evidence. Use QLIKE for variance forecasts and suitable error/loss for excursion outputs. |
| ATR, range width, realized variance, forecast excursion width | Related scale measures but different units and horizons | Normalize only with a documented transform; freeze target and scale. Do not feed a future forecast bound into the feature set that generated it. |
| KMeans/neural market regime, TwoSpeedMarketState, heuristic volatility stress, regime certainty | State/regime/uncertainty summaries may reuse the same underlying price/volatility inputs | Treat as alternative encodings or nested blocks. Verify the feature lineage and training sample of any learned classifier. A `READY` status is not evidence of valid state probabilities. |
| Directional GBDT probability, trend rules, structure detector side | Related directional information and candidate-generation logic | Keep setup side fixed by its approved detector. Evaluate the directional model as a separate feature block; prevent duplicated target leakage and post-selection conditioning. |
| Order-book imbalance, OFI, CVD, depth, spread, impact | Often share the same L2 events and are highly collinear; source/venue coverage can vary | Use an event-data availability gate; compare individual grouped blocks and conditional permutation. Keep execution-quality metrics distinct from directional alpha. Current OHLCV snapshot does not contain these inputs. |
| Funding, open interest, liquidation measures | Derivative positioning/stress family; can share vendor or timestamp lineage | Require source-specific event and publication timestamps; align only as-of. Liquidation data is unavailable in inspected snapshot. No OHLCV proxy is acceptable. |
| Data reliability, model agreement, regime certainty, signal-quality gauge | Heuristic composites may reuse inputs and create circular confidence | Display as diagnostics with transparent components; do not feed a derived score back into the same model without an explicit nested design. No calibrated probabilities implied. |
| Risk budget, cost model, execution simulator, strategy selector | Decision constraints may be mistaken for features | Keep as frozen eligibility/utility calculations after candidate generation. Do not allow risk-gate values to leak labels or tune outcomes. |

## Incompatible contracts to keep separate

- 1-minute fill/path data, 15-minute decision bars, hourly snapshot bars, 24-hour RV target, and 168-hour RV target cannot be joined by row position or assumed common horizon.
- Close-based or 15-minute structural features need fully closed bars; a forming high/low/close cannot enter an earlier decision.
- A range/excursion forecast, a directional up/down classifier, a volatility forecast, and a three-class barrier outcome probability are different estimands.
- Model training, probability calibration, threshold selection, and final evaluation require chronologically disjoint samples.
- Funding/OI records in separate stale local files cannot be treated as contemporaneous with a later Bitstamp candle without explicit point-in-time alignment and eligible provenance.
- Execution cost assumptions in a frozen contract are scenario assumptions, not market observations or evidence of actual fill quality.

## Testable redundancy plan

For each frozen walk-forward fold, fit transformations only on training data; report pairwise Spearman correlations and condition numbers as diagnostics; then perform block ablation plus grouped conditional permutation on validation folds. Use outcome-interval purging and cluster/sequence-aware uncertainty. Keep every attempted feature group in the multiplicity registry. Do not use any final holdout observation for feature ordering or threshold decisions. Full acceptance criteria are in [V36_1_FEATURE_ABLATION_PROTOCOL.md](./V36_1_FEATURE_ABLATION_PROTOCOL.md).
