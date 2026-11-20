# BTCognitive V31.2 — Evidence Verification Report

**Date:** 2026-10-23  
**Status:** `BLOCKED — SOURCE OR CONTRACT UNVERIFIED`  
**Scope:** Research-only repository evidence verification. No strategy implementation, no tournament, no performance claims, no live behavior.

## 1. Decision summary

The repository contains multiple candidate BTC data sources, but the evidence does not support a single verified source identity and timing contract for the entry-research path. The observed blockers are not produced by the strategy logic; they are upstream source-provenance issues:

- the Bitstamp 1-minute file is structurally clean but its timestamp role and historical availability semantics remain unresolved;
- the Coinbase 15-minute path is a different granularity and has no approved use record for the pre-registered 1-minute path;
- the Binance hourly path is a different venue/instrument and is mislabeled in V12;
- the repository contains contradictory historical statements about rights, timestamps, and validation status.

This means there is no defensible single-dataset path yet. Strategy work remains blocked pending a verified single-source contract.

## 2. Repository evidence checked

The following evidence was inspected directly where present:

- `research/entry_tp_sl/data_intake_manifest.json`
- `research/entry_tp_sl/provenance.template.json`
- `research/entry_tp_sl/G0_FOUNDATION_INTEGRITY.md`
- `research/entry_tp_sl/g0_closure_report.md`
- `data/ingest_real_historical.py`
- `research/v12_strategy_tournament_engine.py`
- `engine/barrier_resolver.py`
- `engine/entry_contracts.py`
- `engine/coinbase_15m_adapter.py`
- `engine/execution_cost_model.py`
- `research/protocol_v1_1.md`
- `research/protocol_v1_2_proposal.md`
- `research/protocol_v1_2_decision_matrix_v31_1.md`

## 3. Independently verified findings

### 3.1 Bitstamp file is structurally clean but not provenance-cleared

**Evidence: **
- `research/entry_tp_sl/data_intake_manifest.json` asserts `dataset_status = "VERIFIED_LOCAL_SNAPSHOT"`, `pit_contract_status = "VERIFIED_60S_BAR_CLOSE"`, and `approved_for_research = true`.
- `research/entry_tp_sl/provenance.template.json` explicitly records `timestamp_role = "UNVERIFIED"`, `available_time_rule = null`, and `status = "UNVERIFIED"`.
- `research/entry_tp_sl/G0_FOUNDATION_INTEGRITY.md` states the dataset is a candidate only and that the archive, hash mapping, timestamp semantics, `available_time`, rights, and ShareAlike compatibility remain unverified.
- `research/entry_tp_sl/g0_closure_report.md` later states a pass conclusion, but that closure is historical evidence that directly conflicts with the unresolved provenance template and the earlier G0 gate language.

**Observed behavior:** the repository contains an internally contradictory lineage story for the same Bitstamp dataset. Structural checks (0 null cells, no invalid OHLC rows, no duplicates) do not resolve whether the timestamp denotes open time, close time, or availability time.

**Risk:** a dataset can look clean while still being unusable for point-in-time TP/SL or holdout research, because bar semantics are not equivalent to execution-time availability.

**Next action:** quarantine this as a candidate requiring provenance reconciliation before any replay or strategy evaluation.

### 3.2 Coinbase 15-minute data is a different product and a different research question

**Evidence:**
- `engine/coinbase_15m_adapter.py` documents `GRANULARITY_15M = 900` and explicitly filters the current forming bucket.
- The local manifest in `data/raw/coinbase_15m_manifest.json` records `granularity_seconds = 900` and `first_candle_utc` / `last_completed_candle_utc`.
- Coinbase API docs state `time` is the bucket start, not an availability time or a 1-minute subbar path.

**Observed behavior:** the dataset supports a 15-minute context study, but it cannot support the preregistered 1-minute path or same-bar TP/SL resolution logic.

**Risk:** a 15-minute dataset can be useful for context, but it does not satisfy the contract for 1-minute entry/TP/SL modeling or intrabar barrier resolution.

**Next action:** keep it quarantined for a separate 15-minute-context study only, not for the entry research path.

### 3.3 Binance hourly data is separate from the active research contract

**Evidence:**
- `data/ingest_real_historical.py` fetches `BTCUSDT` 1-hour candles and stores `available_time = timestamp + 1 hour`.
- `research/v12_strategy_tournament_engine.py` labels the dataset as Coinbase BTC-USD and mixes cost scenarios with the Binance perpetual assumption.

**Observed behavior:** the code and data claim different venues and products; the active strategy runner has a venue mismatch and uses historical costs in a way that is not backed by a single verified input path.

**Risk:** mixing Binance and Coinbase under a single strategy contract invalidates source identity and cost interpretation.

**Next action:** quarantine Binance as a separate dataset unless it is explicitly re-registered for a distinct, explicitly separate research contract.

### 3.4 The repository’s own contracts are not aligned to a single accepted source

**Evidence:**
- `engine/entry_contracts.py` defines an immutable candidate contract but does not embed a verified source manifest or a dataset identity hash at the contract boundary.
- `engine/barrier_resolver.py` resolves against provided OHLC bars and does not validate source provenance or minute-path availability as part of the decision contract.
- `engine/execution_cost_model.py` contains multiple cost scenarios whose assumptions are not tied to a single verified instrument contract.

**Observed behavior:** the code is structured as if the inputs were already valid, but the data provenance and source contract remain unresolved.

**Risk:** the error is upstream but it is encoded into downstream logic. Strategy code cannot fix a source-identity bug.

**Next action:** keep the logic in `KEEP`/`REVIEW`, but do not allow it to act as proof of source validity.

## 4. Source comparison table

| Source | Venue | Instrument | Market type | Granularity | Timestamp semantics | Legal / use evidence | Current status |
|---|---|---|---|---|---|---|---|
| `data/raw/btcusd_1-min_data.csv` | Bitstamp | BTC/USD | spot | 1-minute | Unresolved: dataset says 60s bar but provenance template still marks `timestamp_role` and `available_time_rule` as unverified | CC BY-SA 4.0 declared; rights record conflicted with earlier G0 language | `QUARANTINE` |
| `data/raw/coinbase_15m.parquet` | Coinbase Exchange | BTC-USD | spot | 15-minute | `time` is bucket start; no persisted `available_time`; not equivalent to 1-minute decision path | API terms exist, but local snapshot use approval is absent | `QUARANTINE` for main path; `EXPLORATORY ONLY` for 15m context |
| `data/raw/ohlcv.parquet` | Binance BTCUSDT | BTC/USDT | perpetual or spot-like futures access path in code; not the same as Coinbase BTC-USD | 1-hour | `available_time = timestamp + 1h`; separate from the V12 venue labeling | No dataset-specific accepted rights record for this research path | `QUARANTINE` |
| Funding assumptions | multiple sources | variable | hypothetical / scenario-specific | variable | not historical evidence without a verified source contract | not independently validated | `REVIEW` |

## 5. Root cause classification

**Primary root cause:** the repository treats multiple BTC data sources as if they were interchangeable, but the sources differ by venue, product, resolution, and timestamp semantics. The mismatch is not merely a data-cleaning issue — it is a source-contract issue.

**Secondary root cause:** historical reports and manifests conflict with one another, so the repository has no single monolithic provenance record that all downstream code can rely on.

**Third root cause:** the codebase is structured to consume a valid source contract without asserting that the contract itself has passed a proof gate.

## 6. Recommended classification of files

### KEEP
- `engine/entry_contracts.py` — useful immutable candidate contract scaffold, but not sufficient evidence of valid source data.
- `engine/barrier_resolver.py` — useful conservative barrier logic, but not a source-approval mechanism.
- `engine/coinbase_15m_adapter.py` — useful as a bucket-start adapter, but only for narrow context research.
- `engine/execution_cost_model.py` — useful as a scenario catalog, but not as historical cost proof.
- `research/protocol_v1_1.md` and `research/protocol_v1_2_proposal.md` — keep frozen and historical; do not silently overwrite.

### QUARANTINE
- `data/raw/btcusd_1-min_data.csv` as the primary research input until provenance is reconciled.
- `data/raw/coinbase_15m.parquet` for the 1-minute entry path.
- `data/raw/ohlcv.parquet` as an active source unless separately re-registered under a distinct identity contract.
- historical “passed” closure claims where the data contract is structurally clear but provenance and timing remain unresolved.

### REPAIR
- the dataset provenance manifests and source identity documentation, not the strategy logic; fix the contract records, not the strategy.
- add an explicit `available_time` and `source_identity` requirement to any future accepted manifest.

### REVIEW
- older G0 reports and closure reports with conflicting findings; preserve them, but do not treat them as proof of current validity.

## 7. Gate-by-gate status

| Gate | Status | Reason |
|---|---|---|
| G1 — Venue and instrument identity | `FAIL` | Bitstamp and Coinbase and Binance do not share a unified venue/instrument contract. |
| G2 — Timestamp semantics | `UNVERIFIED` | Bitstamp timestamp role remains unresolved; Coinbase bucket-start semantics are documented but different from target path. |
| G3 — Point-in-time availability | `UNVERIFIED` | No persisted `available_time` contract for the active source. |
| G4 — Data integrity | `PARTIAL` | Structural cleanliness exists, but coverage and gap semantics remain under-verified for the chosen research question. |
| G5 — Provenance and permitted use | `FAIL` | Conflicting rights and version claims; legal-use scope not clear. |
| G6 — Deterministic replay | `UNVERIFIED` | No single accepted data manifest or fixed timing contract. |
| G7 — Holdout integrity | `UNVERIFIED` | No common frozen holdout has been validated under one source contract. |
| G8 — Barrier-resolution limitations | `UNVERIFIED` | The granularity and path semantics are not settled. |
| G9 — Execution-cost assumptions | `UNVERIFIED` | Costs remain hypothetical or scenario-based. |
| G10 — Integrity baseline | `FAIL` | The initial entry-ledger baseline hash was malformed / invalid as a SHA-256 string; cannot be used as a proven integrity baseline. |
| G11 — Independent review | `UNVERIFIED` | Independent review is not a substitute for source-proof; the repo still needs a traceable identity contract. |

## 8. Recommended next action

The safest next action is not to choose a strategy or optimize a code path. It is to stop and require a single defensible source contract before any replay or strategy work resumes.

**Recommended next step:** choose one source only after all of the following are satisfied:

1. venue and product identity are consistent end to end;
2. timestamp semantics and `available_time` are documented by primary-source evidence;
3. rights/use permission is explicit and scoped to research;
4. a deterministic data manifest exists for that source only;
5. the holdout and replay contract are frozen before any evaluation.

If those conditions cannot be met, the recommendation remains:

**`BLOCKED — SOURCE OR CONTRACT UNVERIFIED`**

## 9. Final conclusion

The repo is not blocked because the strategy logic is bad; it is blocked because the source layer is not defensible. The research stack should not proceed to strategy tuning, tournament evaluation, or live behavior until one source has a verified identity, availability-time contract, rights record, and deterministic replay boundary.
