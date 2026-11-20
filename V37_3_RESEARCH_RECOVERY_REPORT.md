# BTCognitive V37.3 — Research Recovery Report

**Workstream:** 2 — research recovery

**Assessment date:** 2026-11-04

**Repository state observed:** `milestone/v35.3-critical-remediation` at `25d483f4c3646661b57311de9d0b53d2be881adb`; the worktree was already broadly modified. This report is the only file created for this workstream; existing changes were preserved.

**Mode:** Static provenance/feature audit plus synthetic mechanics regression tests. No market-data research, replay, model fitting, tuning, or performance evaluation.
**Decision:** Historical validation is blocked by unresolved provenance and point-in-time/execution contracts. Preserve the existing institutional BTCUSD intelligence and risk-research architecture; do not promote or authorize execution.

## Executive decision and boundaries

BTCognitive's research purpose remains BTCUSD market-structure, volatility, regime, uncertainty, and excursion/risk intelligence—not broker execution or a claim of trading profitability. Existing forecast, feature, and `research/entry_tp_sl` implementations are retained as separate research/application paths; this report neither replaces their contracts nor treats code presence as evidence of predictive validity.

| Track | Intended role | Admissibility decision in this workstream |
|---|---|---|
| **Track A — hourly** | Descriptive structure, HAR/realized-volatility features, regime/state and other hourly OHLCV features. Volatility accuracy and descriptive regime properties remain distinct from return direction or entry execution. | Coinbase BTC-USD V2/V3 hourly snapshots are a **candidate for bounded historical Track A work**, not a presently `VERIFIED` provenance record under the research provenance schema. Source authenticity is not independently established, there are documented missing hours, and this workstream did not freeze a selection-free analysis window/protocol. No actual Track A computation was run. Track A results, if separately authorized later, must be descriptive/research-only and cannot validate Track B. |
| **Track B — minute** | Existing 15-minute setup/decision plus 1-minute entry, barrier, cost, and outcome research in `research/entry_tp_sl`. | **Not admissible for market-outcome research.** The claimed Bitstamp BTC/USD minute file remains `UNVERIFIED` for source authenticity and timestamp role/availability; the fill/path mapping and several frozen execution rules remain unresolved. No minute rows, labels, or outcomes were used. |

No Coinbase/Bitstamp series were combined. No hourly observation was treated as a minute fill, barrier path, or execution label. No protected holdout was used for feature/model selection or outcome evaluation. No live data request, trading, or real-capital execution occurred.

## Provenance status vocabulary

The `research/entry_tp_sl/schemas/provenance.schema.json` status enum is used without inventing a stronger status: `VERIFIED`, `UNVERIFIED`, `PROVENANCE_FAILURE`, `DATA_UNAVAILABLE`, `MODEL_FAILURE`, and `NO_SIGNAL`. `UNVERIFIED` means evidence is insufficient to attest the full source/instrument/time semantics contract; it does not mean the bytes are corrupt. “Hash matches manifest” is reported only as local byte-identity evidence, not as provider authentication. `VERIFIED_LOCAL_SNAPSHOT`, where found in an older manifest, is not treated as equivalent to schema status `VERIFIED`.

## Dataset admissibility register

All dates below are the UTC ranges recorded in existing manifests/audits; row counts are recorded values, not newly recomputed counts. No dataset was opened for analysis in this workstream.

| Existing source and stated coverage | Missingness, time semantics, and evidence | Status and permitted use |
|---|---|---|
| `data/research/coinbase_btc_usd_hourly_verified_v2/coinbase_btc_usd_hourly.parquet`; Coinbase BTC-USD, 1h; 42,237 rows; 2022-01-01 00:00 through 2026-10-27 09:00. V3 is byte-identical with the same count, interval, and range. | V36.2 records matching local hashes/manifests, 13 missing hours in three documented intervals (2023-03-04 18:00–20:00, 2025-10-25 16:00–20:00, 2026-05-08 02:00–06:00 UTC), no gap filling, UTC candle-open timestamps, and `available_time = open + 1h`. The acquisition/authentication claim is not independently verified. V3 adds no independent history. | **`UNVERIFIED` for full source provenance**; the local snapshot/hash and documented timing rule are recorded. Candidate only for a separately frozen, bounded hourly Track A descriptive study, with gap-aware treatment and an explicit excluded-date/window policy. Not admissible for Track B, confirmatory claims, or current-market use. |
| `data/research/coinbase_btc_usd_hourly_v1/coinbase_hourly.parquet`; Coinbase BTC-USD, 1h; 33,424 rows; 2023-01-01 00:00 through 2026-10-25 04:00. | Manifest records Coinbase API acquisition; 13 missing hours in three intervals; the authentication claim is not independently verified. | **`UNVERIFIED`** for full provenance. Superseded as a candidate by byte-identical V2/V3 for coverage; do not pool versions as independent samples. |
| `data/raw/coinbase_15m.parquet`; Coinbase BTC-USD, 15m; 16,200 rows; 2026-05-10 23:45 through 2026-10-26 17:30. | V36.2 records no gaps/duplicates/basic OHLCV anomalies, but open-time semantics are inferred rather than explicit. Short span (~169 days). | **`UNVERIFIED`** for timestamp semantics; not a substitute for Bitstamp minute execution paths or multiyear validation. |
| `data/raw/btcusd_1-min_data.csv`; claimed Kaggle `mczielinski/bitcoin-historical-data` v745 / Bitstamp BTC/USD spot, 1m; manifest reports 7,766,111 rows, 2012-01-01 00:01 through 2026-10-07 03:11; SHA-256 `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`. | Manifests report 0 nulls, monotonic Unix-second UTC timestamps, no duplicates and valid OHLC bounds. These are repository-reported structural checks, not source authentication. Intake/contract records assert interval-close/`VERIFIED_60S_BAR_CLOSE`, while provenance/template records leave source binding, timestamp role, and `available_time` unresolved. Gap tolerance is not numerically frozen. V36.3 documents a concrete mismatch between the declared close-stamp convention and the runner's fill-row/open mapping. | **`UNVERIFIED`**; exact local bytes match the listed digest, but source authenticity, physical bar-time meaning, and causal availability are unresolved. **Exclude from all Track B outcome/model selection.** |
| `data/providers/bitstamp/BTCUSD_1h.parquet`; claimed Bitstamp BTC/USD, 1h; 1,000 rows; 2026-09-22 23:00 through 2026-11-03 14:00. | V36.2 records matching provenance hash, no reported gaps/duplicates/basic OHLCV anomalies, but prior gate classifies this short local snapshot as stale for current-market analysis. | **`UNVERIFIED`** as research evidence; short hourly descriptive context only if independently re-attested. Never use to form minute execution labels. |
| Other Bitstamp hourly snapshots (`BTCUSD_1h_v34_2_multiyear.parquet`: 1,000 rows, 2024-01-01–2024-02-11; `BTCUSD_1h_v34_expanded.parquet`: 4,000 rows, 2026-05-20–2026-11-02). | The “multiyear” filename is not multiyear coverage. The expanded file's provenance does not itself specify exchange/pair and lacks raw-payload hash per V36.2. | **`UNVERIFIED`**; exclude from pooled evidence, model selection, and any claimed continuous history. |
| `data/raw/ohlcv.parquet` and related unnamed raw snapshots; current file reported as 42,326 hourly rows, 2022-01-01 through 2026-10-30 13:00. | No acquisition manifest establishes source/pair/time semantics. V36.2 found material value differences versus Coinbase V2 despite timestamp overlap; these files are not interchangeable. | **`PROVENANCE_FAILURE` for source-attributed research** (lineage cannot be established); exclude. No attribution based on code comments or filename. |

### Protected holdout and existing sample counts

`research/entry_tp_sl/holdout_custody_manifest.json` records holdout `SEALED_HOLDOUT_BTC_2025_2026`, 2025-10-08 through 2026-10-07, 2,662 trades, status `SEALED_UNTOUCHED`, and authorizes opening only after prospective protocol registration and model freeze. Its manifest count/status were read as governance metadata only; no holdout observations, labels, or row values were inspected or used. Keep the cohort sealed and unavailable for model/feature selection.

The pre-existing 6B implementation/pilot manifests record a 500-row pilot label set: 196 `TP_FIRST`, 283 `SL_FIRST`, and 21 `TIMEOUT`; 3 collisions are separately recorded as a subset/ambiguity count, not additional independent rows. The manifests bind this to the same unverified minute-file digest and do not establish that the sample is outside the protected holdout. It is therefore **not admissible evidence**, is not reproduced here, and is not a performance result. For this report, eligible Track B observations and model-evaluation sample size are **0**; no new candidate count, excluded-row count, trade rate, or metric was computed.

## Feature-family role, coverage, and execution status

Lifecycle counts in `V36_2_FEATURE_RUNTIME_READINESS.md` describe **32 ENG groups**, not individual feature columns: 17 `ACTIVE_UNVALIDATED`, 8 `EXPERIMENTAL`, 4 `DATA_UNAVAILABLE`, 2 `DISABLED`, 1 `BROKEN`, and 0 `ACTIVE_VALIDATED`. V36.2 states no feature was executed in that audit. Source presence, test coverage, runtime reachability, feature calculation, PIT correctness, and predictive validation are separate states.

| Feature family | Intended track and existing implementation/role | Coverage, status, and boundary |
|---|---|---|
| Hourly OHLCV, returns, trend/momentum, ATR/ADX/EMA/VWAP, RSI, volume/range and rolling technical features | Track A descriptive market structure/features. Existing feature pipeline and state/technical modules remain separate from entry/exit labels. | Computable only from a provenance-qualified, cadence-matched hourly series with explicit closed-bar/availability cutoffs. The V2/V3 candidate has 42,237 hourly rows and 13 documented missing hours; gap handling must preserve rather than fill those intervals. No coverage matrix or current feature rows were computed. `ACTIVE_UNVALIDATED`/experimental lifecycle is not a validation result. |
| HAR / realized variance and semivariance | Track A volatility and risk characterization. `engine/har_24h_features.py` includes 24/168/720-hour lags and a distinct future 24-hour realized-variance target; it is not direction prediction. | The `rv24h_var_ann` target is separate from the 168-hour target. Standard HAR registry artifact is `BROKEN`/absent with placeholder identity; frozen HAR-RS-DOW is `OFFLINE_RESEARCH_ONLY`, its training input hash differs from current raw OHLCV and the recorded IV7d file is absent. No HAR training, forecast, or loss computation was run. Never infer minute execution validity from hourly HAR. |
| Regime, market-state, volatility-stress/certainty and uncertainty diagnostics | Track A descriptive/risk context; output must remain distinct from a validated regime or calibrated probability. | Existing groups are `ACTIVE_UNVALIDATED` (some model paths experimental); valid historical features depend on input provenance/PIT. Uncertainty coverage is not established; C2 remains disabled. No regime fit, calibration, or feature contribution was run. |
| Structural setups and entry/PIT features | Track B only. `research/entry_tp_sl/pit_features.py` contains rolling ATR, realized/Parkinson volatility, returns, RSI, volume ratio, SMA distance and UTC-time features; `setup_detector.py` contains A1 sweep/reclaim and A2 range/reclaim. | Feature code is present and `EXPERIMENTAL`, but there is no admissible minute source execution. The pipeline resamples without explicit `closed`/`label`, does not enforce each input's `available_time <= decision_time`, and current A1 detects same-bar sweep/reclaim despite the two-bar specification. No feature vectors, coverage rates, or setup samples were computed. |
| Barrier, outcome, excursion and execution-cost features | Track B only. Existing `triple_barrier.py`, `reference_resolver.py`, frozen entry/outcome contracts, and cost scenarios define research mechanics; keep separate from the application execution simulators. | Source/tests exist, but real outcome validity is blocked by timestamp/fill alignment, entry-gap rule, incomplete/missing path handling, opening-gap/dual-touch ordering, and cost/slippage accounting questions described in V36.3/V37.2. No market labels, costs, win rates, MFE/MAE, or profitability metrics were computed. |
| Order book/microstructure (imbalance, spread, OFI, CVD, depth, impact), trades, derivatives (funding/OI/liquidations), macro, sentiment and on-chain | Potential context/features only with synchronized, timestamped, source-specific feeds. | **`DATA_UNAVAILABLE`** for this local evidence set; no OHLCV proxy or synthetic substitute. Not covered by either track's present admissible feature sample. |
| Directional classifiers, candidate strategies, forecast intervals, risk metrics, selection, and paper/execution simulators | Remain distinct product/research capabilities; candidate generation, volatility, direction, calibration, and execution are not interchangeable targets. | Mostly `EXPERIMENTAL`/`ACTIVE_UNVALIDATED`; no calibrated direction, TP/SL probabilities, measured fills, or validated risk-adjusted result established here. Candidate signals are not orders. No authorization change. |

`research/entry_tp_sl/data_intake_manifest.json` explicitly excludes reused HAR OHLCV, IV7d, HAR artifacts, and hourly OHLCV substitutes from the minute track. This separation is preserved.

## Point-in-time and causal gate

- **Track A:** the Coinbase V2/V3 acquisition manifest specifies candle-open timestamps and availability one hour after open. Any hourly feature for a decision at time `t` must be built only from bars whose recorded availability is `<= t`; the future `rv24h_var_ann`/`rv7d_var_ann` targets are labels, never inputs. Hour gaps remain explicit. No features were built, so no PIT pass is claimed.
- **Track B:** the minute source's timestamp role and availability rule are unresolved and conflicting across repository records. Under the frozen interval-close assumption, the pipeline's exact `t0 + 60s` row/Open fill mapping is inconsistent with the physical bar interval; timestamp resampling is also not explicitly closed/labeled. Until the source role and index mapping are resolved, causal alignment is **`UNVERIFIED`**. A backward-looking rolling window alone does not establish PIT correctness.
- **Cross-track boundary:** Track A hourly observations can support, at most, hour-scale descriptive/volatility questions under their own dataset contract. They cannot establish 15-minute setup timing, a next-minute fill, intrabar barrier resolution, spreads, slippage, or minute costs. No resampling, venue stitching, or proxy inference bridges this gap.

## Execution record, commands, and no-run rationale

### Market research no-run

No actual Track A or Track B research was run. For Track A, the locally documented Coinbase snapshots are candidates but do not reach schema status `VERIFIED`; source authentication remains a manifest claim, and no selection-free analysis window/protocol was frozen for this report. For Track B, the claimed Bitstamp minute file remains `UNVERIFIED`, the protected cohort must stay sealed, and the frozen resolver/execution contract is not fully implementable against the unresolved timestamps. These are admissibility blockers, not null findings. No market data, holdout rows, model-selection result, or performance estimate is implied.

The existing `research/entry_tp_sl/run_full_research_pipeline.py` was not run: it reads the unverified minute CSV and writes labels, ledgers, and research artifacts. The minute file, existing pilot-label sample, and persistent ledgers were not used as observations in this workstream. No external data or live market request was made.

### Synthetic mechanics verification

The safe, deterministic entry/barrier tests were run only as **`PIPELINE_TEST_ONLY`** mechanics checks; their fixtures are not BTC market observations and do not establish data admissibility or model performance.

First command used an incorrect test path and collected no tests:

```powershell
.\.venv_win\Scripts\pytest.exe -q research\entry_tp_sl\tests\test_pit_invariants.py ...
```

Result: `ERROR: file or directory not found`; no tests ran.

Corrected focused command:

```powershell
.\.venv_win\Scripts\pytest.exe -q tests\entry_tp_sl\test_pit_invariants.py tests\entry_tp_sl\test_barrier_contract.py tests\entry_tp_sl\test_cost_accounting.py tests\entry_tp_sl\test_resolver_differential.py tests\entry_tp_sl\test_timeout_accounting.py tests\entry_tp_sl\test_intrabar_ambiguity.py tests\entry_tp_sl\test_triple_barrier.py
```

Result: **76 passed in 8.97s**. The protected-file integrity guard reported **PASS** for its 1,848-file inventory (data/results/experiment results/research/models), with matching before/after manifest digest `d424b3c0dd43a0b4a91735a2050fd43315edd341d3f146655aad6698ec3ce031`. This was a test-harness integrity check, not observation analysis or model selection. The full suite, application/API lifespan, market replay, and data feature coverage were not run.

## Required recovery gates

1. **Track A admission:** obtain/record complete source and rights evidence for a specific immutable Coinbase BTC-USD hourly snapshot; pin the exact time window, pre-holdout exclusion boundary, feature/target definitions, gap policy, and descriptive-only analysis before computation. Keep all data at or after the protected cutoff out of selection. Do not equate manifest hash matches with source authentication.
2. **Track B admission:** supply already-authorized immutable source/acquisition evidence for the claimed Bitstamp BTC/USD minute artifact; resolve its open/close role and `available_time`; specify a numerical gap tolerance and an exact `t0`, fill, and path-row mapping. Independently resolve entry-gap, opening-gap/dual-touch, full-horizon/missing path, A1 reclaim, short-spot, tick rounding, and single-count cost conventions against the frozen contracts.
3. **Holdout governance:** retain `SEALED_UNTOUCHED`; establish access controls and a frozen protocol before any authorized opening. The manifest's 2,662-trade count is not evidence that custody controls were effective.
4. **Feature/runtime accounting:** only after data admission, produce per-feature input coverage/missingness, warm-up exclusions, gap exclusions, causal availability checks, and executable-row counts separately for each track. Keep unavailable streams explicitly unavailable; do not manufacture neutral/synthetic empirical features.
5. **Evidence threshold:** keep retrospective replays and prior reports labeled retrospective. Prospective confirmatory evaluation remains gated on at least 100 clean, non-overlapping mature blocks after protocol/model freeze; hourly validation cannot satisfy minute execution validation.

## Evidence basis

This recovery report synthesizes existing repository records and source review; it does not revise or silently replace prior findings:

- Dataset coverage and lineage: `V36_2_DATA_AND_LINEAGE_ADMISSIBILITY.md`, Coinbase V2/V3 acquisition manifests, and `research/entry_tp_sl/data_intake_manifest.json`.
- Minute-source provenance and holdout: `V36_3_DATA_PROVENANCE_ATTESTATION.md`, `research/entry_tp_sl/holdout_custody_manifest.json`, `contract_freeze_manifest.json`, and `6B_implementation_manifest.json`.
- Feature lifecycle/runtime: `V36_1_FEATURE_REGISTRY.csv` and `V36_2_FEATURE_RUNTIME_READINESS.md`.
- Frozen minute contracts: `V36_3_FROZEN_CONTRACT_CONFORMANCE.md`, `research/entry_tp_sl/decision_contract.json`, `entry_execution_contract.json`, `instrument_contract.json`, and `outcome_accounting_contract.json`.
- Pipeline and prior no-run evidence: `V37_2_ANALYSIS_AND_BACKTEST_REPORT.md`; implementation reviewed conceptually at `research/entry_tp_sl/run_full_research_pipeline.py`, `pit_features.py`, `setup_detector.py`, `triple_barrier.py`, and `reference_resolver.py`.

## Governed release decisions

1. **Research experiment:** `INCONCLUSIVE` — no admissible market experiment was run; synthetic mechanics only.
2. **Prospective evidence:** `NOT_STARTED` — no new prospective evidence was collected or resolved.
3. **Model authorization:** `OFFLINE_RESEARCH_ONLY` — no model, feature, or result is promoted.
4. **Live trading:** `DISABLED` — no broker/order/real-capital activity.
