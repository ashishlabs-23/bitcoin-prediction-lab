# BTCognitive Entry/TP/SL Research Track — G0 Foundation Integrity

**Track:** BTC-ENTRY-TP-SL-V3  
**Date:** 2026-10-07  
**Status:** `G0 BLOCKED — DO NOT PROCEED TO 6A.`

This is a new 15-minute decision / 1-minute path-resolution research track. It is separate from the blocked 7-day HAR-RS-DOW product. No detector was tuned, no model was trained, no trading result was generated, no source dataset was downloaded, and no HAR artifact or IV feature is an input to this track.

## 1. Repository and Runtime Inventory

| Item | Finding |
|---|---|
| Repository layout | Python API/backtest/engine/models/research/training/validation, web UI, parquet/SQLite data. New track lives only under `research/entry_tp_sl/` and `tests/entry_tp_sl/`. |
| Python | CPython 3.13.14, Windows x64; selected interpreter is the system Python, not an isolated research venv. |
| NumPy / pandas / SciPy | 2.3.2 / 3.0.5 / 1.18.0 |
| scikit-learn / LightGBM | 1.9.0 / not installed |
| pytest / pluggy | 8.4.1 / 1.6.0 |
| pytest plugins | Root runtime: `anyio` 4.13.0 and `pytest-asyncio` 0.23.7; no timeout plugin. Isolated research venv: `pytest-timeout` 2.4.0. xdist and randomly are not used. |
| Relevant installed packages | XGBoost 3.4.0, PyArrow 25.0.1, joblib 1.5.3. They are not required by the new CSV-only G0 dataset path except PyArrow may support unrelated repository tests. |
| Existing pytest config | `pytest.ini`: `testpaths=tests`, excludes environment/vendor/web/archive/experiment directories, registers `network`. No default timeout or global selection filter. |
| Collection | 689 existing test nodes at this audit. |

Current research environment files: `.python-version`, `requirements.in`, platform-specific hash lock `requirements.lock`, deterministic `runtime.env`, and `environment_fingerprint.py`. The hash lock resolves 29 Windows CPython 3.13.14 distributions, including LightGBM, Hypothesis, jsonschema, and pytest-timeout. Pip dry-run resolution was verified against each locked package/version/archive SHA-256. A temporary venv at `%TEMP%\\btcognitive-entry-tp-sl-20261007` was instantiated from that lock; no packages were installed to the system or project interpreter. The lock is Windows x64-specific, not cross-platform. The fingerprint hashes the version pin, direct requirements, lock, runtime settings, fingerprint script, and installed distribution list. Fingerprint observed in the isolated venv: `1f327cf5edf52a160282f6f2f08ad8b4536a161851dc5cea4e25cfa770c6ea62` (`READY`). The isolated G0 suite passes 4 tests. A second clean-environment replay remains required before research results can be claimed.

Determinism settings pin `PYTHONHASHSEED=0`, `TZ=UTC`, and numerical thread counts to 1 before launching Python. `TZ` is recorded as process intent; timestamps must still be explicitly parsed/serialized as UTC, especially on Windows. LightGBM estimators must additionally set `deterministic=True`, `force_row_wise=True`, and explicit seeds/thread count when that phase is authorized; those parameters are not set in G0.

## 2. Data Snapshot Contract

The current repository contains `data/raw/ohlcv.parquet` (40,902 rows; median adjacent spacing 60 minutes; minimum 60 minutes; maximum 120 minutes) and no 1-minute/sub-minute bars, trades, or order-book path snapshot. Thus local required path data is **`DATA_UNAVAILABLE`**. The hourly file has a changed HAR hash and is explicitly not reused.

Verified public candidate metadata:

- Kaggle dataset `mczielinski/bitcoin-historical-data`, version 745, created 2026-10-07, file `btcusd_1-min_data.csv`, 393,952,273 bytes.
- Publisher identifies it as Bitstamp BTC/USD spot, 1-minute OHLCV and BTC volume; gaps may occur.
- Kaggle declares CC BY-SA 4.0. Publisher automation says timestamps are Unix seconds and fetches 60-second Bitstamp OHLC bars.
- This is a **candidate**, not a materialized research snapshot. The archive, row count, SHA-256, candle boundary semantics, `available_time`, gap/duplicate audit, Bitstamp data terms, and ShareAlike compatibility have not been verified.

The schema and template are at `schemas/dataset_manifest.schema.json` and `dataset_manifest.template.json`. The template records `DATA_UNAVAILABLE`, the Kaggle candidate metadata, `storage.preferred_backend=google_drive`, and null Drive object ID/URI/hash. A Drive link/file ID and a byte-for-byte verified snapshot are still required. No credentialed Drive/Kaggle access was attempted.

`iv7d.parquet`, IV-derived features, changed HAR OHLCV, and HAR artifacts are explicitly excluded by the manifest template. No synthetic/proxy data is permitted.

## 3. Provenance and Rights

`schemas/provenance.schema.json` and `provenance.template.json` require source/version/license, instrument identity, timestamp and availability-time semantics, artifact SHA-256, transformation hashes, and explicit source exclusions. The state enum distinguishes `PROVENANCE_FAILURE`, `DATA_UNAVAILABLE`, `MODEL_FAILURE`, and `NO_SIGNAL`.

`data_model_rights_checklist.md` records current exchange sources and future checkpoint candidates. Kaggle reports CC BY-SA 4.0; that declaration is captured, but upstream rights and obligations for the intended research/product use remain `REVIEW_REQUIRED`. TimesFM, Chronos, Toto, and Kronos checkpoint licenses/cutoffs are `UNVERIFIED`; none was downloaded.

## 4. Resolver Authority

No canonical `resolution_service` exists. Existing implementations disagree: `backtest.simulate.check_position_closure_high_low` and conditional-path/decision-envelope code use stop-first rules, while `research.target_validation_v2.py` treats dual touches as ambiguous. Existing execution helpers use nominal barrier prices and lack gap/latency/fill semantics. HAR, 24-hour excursion, Hawkes, directional-close, and arena resolvers have different targets.

`resolver_audit.md` enumerates the implementations and callers. G0 selects none. The planned next-stage design is a versioned research resolver plus an independent pure-Python oracle; it is not implemented here.

## 5. Pytest Triage

`pytest_triage_report.md` records the exact bounded-run timeout:

```text
tests/test_candle_manager.py::test_candle_state_manager_forming_vs_closed
```

The stack runs through `api/candle_manager.py` into `backtest/market_memory.update_prediction_outcome()` and `pandas.read_csv()`. The candle manager iterates 5,377 pending records and calls a function that rereads and rewrites the full 5,398-row, 2,788,437-byte CSV for each row. A single read measured 0.077 seconds; repeated full-file read/write is quadratic. This is an existing shared-runtime performance defect. It is tagged `quarantined` with a reason, but remains in default pytest collection; no skip, global exclusion, or `addopts` weakening was added. Its production-side fix is outside this G0 task's requested scope, so the global suite is not G0-clear.

The suspected 73%-position `test_range_failure_modes.py` tests pass alone (3 passed); the preceding quantitative/range DB/range failure sequence passed in isolation with a temporary SQLite path (9 passed). The bounded full suite with `pytest-timeout` produced the candle-manager stack dump. Independent G0 tests are runnable separately with:

```powershell
python -m pytest -q --timeout=30 tests/entry_tp_sl
```

## 6. Resolver / Failure-State Invariants

- `PROVENANCE_FAILURE`: artifact/data lineage, hashes, PIT availability, or time semantics do not verify.
- `DATA_UNAVAILABLE`: required local/remote 1-minute-or-finer path, coverage, or feed is absent.
- `MODEL_FAILURE`: later model/artifact/runtime failure.
- `NO_SIGNAL`: valid computation has no eligible setup or abstains.

None may be converted into a numeric result. An open-position response policy is explicitly out of scope until §11.3 is approved.

## 7. G0 Checklist

| Gate | Status | Evidence / blocker |
|---|---|---|
| Isolated environment definition and exact pins | `PREPARED; TEMP VENV INSTANTIATED` | 29-package hash lock validated in dry-run and installed only in `%TEMP%`; isolated G0 tests still pending. |
| Own dataset snapshot and manifest | `DATA_UNAVAILABLE` | Candidate identified, but no archive/file ID/hash/gap audit exists. |
| 1-minute-or-finer path data | `DATA_UNAVAILABLE` locally | Existing raw OHLCV is hourly only. |
| IV exclusion | `PASS` | Entry/TP/SL schema and template exclude IV and HAR sources. |
| Resolver authority | `BLOCKED` | No canonical resolver; divergent tie policies. Versioned resolver/oracle decision remains for 6A/6B. |
| Pytest triage | `ROOT_CAUSE_IDENTIFIED; SUITE_BLOCKED` | Exact `test_candle_state_manager_forming_vs_closed` timeout and O(N²) CSV update path identified; marker documents it but default collection still runs it. Independent G0 namespace passes 4 tests. |
| Data/model rights | `REVIEW_REQUIRED` | Kaggle license declared, upstream rights/ShareAlike review pending; checkpoint rights remain unverified. |
| Training authorization | `NO` | Multiple G0 gates incomplete. |

**Overall: `G0 BLOCKED — DO NOT PROCEED TO 6A.`** No 6A contracts, labels, detector, model, or results are created here.
