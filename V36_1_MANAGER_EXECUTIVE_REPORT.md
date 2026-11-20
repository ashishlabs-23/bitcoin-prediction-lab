# BTCognitive V36.1 — Manager Executive Report

## Decision

V36.1 completed a read-only, capability-level feature discovery and design package. It did **not** run the analysis engine, tests, network calls, database reads/writes beyond the prior approved snapshot inspection, or model training. The current snapshot is valid against its own stored provenance but stale for a current-market analysis; the existing analysis route exits before the engine. Historical replay is specified separately and **not implemented or approved for execution**.

## Inventory counts (grouped records, not every function)

The feature registry contains **54 grouped records**:

| Group | Registry rows |
|---|---:|
| Frontend surface groups | 10 |
| API route groups | 12 |
| Analytical/data/governance capabilities | 32 |

| Lifecycle classification | Count |
|---|---:|
| `ACTIVE_VALIDATED` | 0 |
| `ACTIVE_UNVALIDATED` | 39 |
| `EXPERIMENTAL` | 8 |
| `DEPRECATED` | 0 |
| `DISABLED` | 2 |
| `DATA_UNAVAILABLE` | 4 |
| `BROKEN` | 1 |

These are registry-record counts, not counts of all capabilities or methods. The source scan counted 2,226 files / 566 Python files in `engine/`, `backtest/`, `models/`, `config/`, and `tests/`. The report explicitly identifies remaining directories and function-level coverage gaps; do not describe the 54 records as an exhaustive count of all repository software.

## Main findings

- **Available for compatible historical calculations:** the exact verified local Bitstamp BTC/USD hourly snapshot contains 1,000 continuous, valid candles and has SHA-256 `d64cd2591b4cc5c5a6328785b1722ec5f8e01b78f30dee7f1dc7dff583e7fc54`. Its latest closed candle is 2026-11-03 15:00 UTC, so it remains `STALE_FOR_CURRENT_MARKET`.
- **Not runnable on the hourly snapshot:** the 15-minute setup/forecast path and 1-minute fill/barrier outcomes need data at finer cadence. Do not resample or infer intrabar path.
- **Unavailable data groups:** order-book/microstructure, liquidation observations, and aligned funding/open-interest inputs require separate authorized, timestamped data. Missing inputs remain unavailable; no synthetic metrics.
- **No demonstrated predictive contribution:** trend/regime/microstructure/uncertainty/strategy feature groups have no V36.1 controlled incremental OOS result. `ACTIVE_UNVALIDATED` and `EXPERIMENTAL` do not mean validated.
- **Model lineage blockers:** Standard HAR registry artifact is absent/placeholder; its accuracy is `NOT_ESTABLISHED`. Current raw OHLCV SHA differs from frozen HAR-RS-DOW training hash. HAR-RS-DOW remains unpromoted.
- **Outcome model gap:** existing B4 components are binary selective classifiers. They are not a calibrated `TP_FIRST`/`SL_FIRST`/`TIMEOUT` model.
- **Frontend/API reachability:** static scan found 191 HTTP route decorator declarations, 190 distinct method/path pairs (one duplicate comparator declaration), 186 distinct path strings, one WebSocket route, and one static mount. 93 method/path pairs had no direct matching frontend URL literal after alias normalization. The app has 57 non-App function components, plus `App`; handler counts are 219 `onClick`, 7 `onSubmit`, and 57 `onChange` sites, not unique user actions.

## Features that can be used together (design only)

Use timestamped, same-source OHLCV validation → causal features → same-horizon volatility/state estimates → approved candidate generation → deterministic risk/cost gates → candidate-conditional outcome probability (only after it is separately trained and validated). Regime and trend features may be tested as incremental blocks. Volatility forecasts may support a risk/excursion analysis but cannot be called directional accuracy. L2 features can be considered only with real timestamped event feeds. Feature groups must not be joined across incompatible timeframes without an explicit availability-aware contract.

## Recommended implementation order

1. Finish source-level inventory across omitted `research/`, `training/`, `validation/`, `calibration/`, `labeling/`, `features/`, remaining API/engine modules, root config and `web_src/`; reconcile API schemas and all frontend value origins.
2. Resolve Standard HAR artifact and data lineage; separately reconcile frozen HAR-RS-DOW source identity without modifying its manifest or promoting it.
3. Implement and independently review isolated `HISTORICAL_REPLAY` contract with explicit as-of, verified hash, no providers/writes, stale badge, authorization OFF, and robust tests.
4. Only exercise snapshot-compatible hourly features after replay gate passes. Report unsupported 15m/1m/L2/derivatives features as unavailable.
5. Before any trade outcome fit, freeze candidate/label/cost/fill semantics; acquire authorized 15m and 1m data; establish label quality, effective sample and chronological split custody.
6. Preregister the controlled feature-ablation and multiclass probability validation protocols; keep final holdout and prospective evidence untouched.

## Exact remaining limitations

No engine run or test result is claimed. No forecast accuracy, hit rate, calibration, regime usefulness, strategy edge, or feature contribution was established. No 15m/1m data or real order-book/funding/OI/liquidation feed was identified in the verified Bitstamp snapshot. Raw HTTP payload bytes are absent, so raw-response hash cannot be recomputed. Current raw parquet and frozen HAR-RS-DOW training hashes do not match. Standard HAR artifact is not recovered. The protected prospective and market-memory stores were not modified; this report does not certify their integrity. The source inventory is grouped and not method-by-method exhaustive. All model capabilities remain `OFFLINE_RESEARCH_ONLY`.

## Governed release decisions

1. **Research Experiment:** `INCONCLUSIVE` — V36.1 is an inventory/design milestone; no predictive experiment ran.
2. **Prospective Evidence:** `COLLECTING` — carried forward from prior [V35_4_3 closeout](./V35_4_3_MANAGER_EXECUTIVE_REPORT.md); [V35_4_2](./V35_4_2_FINAL_INTEGRITY_CLOSEOUT.md) noted 21 overlapping records, not 100 independent clean blocks. V36.1 did not inspect or modify the protected store; current effective sample/precision are not reverified and no sufficiency claim is made.
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`.
4. **Live Trading:** `DISABLED`.

The eventual system should select only the strongest evidence-supported BTCUSD candidate or abstain with `NO_TRADE`. It must not promise a guaranteed winning trade.
