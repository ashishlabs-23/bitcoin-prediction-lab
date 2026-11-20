# BTCognitive V31.1 — Data Provenance Audit

**Review date:** 2026-10-23  
**Repository HEAD at baseline:** `24092a118bb4285cb2675cbc02694d34800d92d5`  
**Branch:** `main`  
**Decision:** `GATE A BLOCKED — NO DATASET SELECTED OR FROZEN`

## Scope and decision

This is a read-only audit of candidate data for an offline historical entry replay. It does not authorize a tournament, strategy tuning, production prediction, or execution. Dataset identity, timestamp semantics, availability time, use rights, and instrument alignment must all be supported before a candidate can be frozen. Structural checks alone do not establish point-in-time validity or executable fills.

No current candidate clears all Gate A requirements. Accordingly, no accepted-dataset manifest was created, no performance replay was run, and no strategy or cost scenario was promoted.

## Candidate inventory

| Candidate | Verified local artifact | Identity and time evidence | Rights / permitted-use evidence | Disposition |
|---|---|---|---|---|
| Kaggle Bitstamp BTC/USD 1-minute CSV, claimed version 745 | `data/raw/btcusd_1-min_data.csv`; 393,952,273 bytes; SHA-256 `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`; 7,766,111 rows; 2012-01-01 00:01:00 UTC through 2026-10-07 03:11:00 UTC | Kaggle and publisher materials identify Bitstamp BTC/USD spot. Publisher automation fetches Bitstamp 60-second OHLC and carries the returned timestamp through; its code does not establish whether that value denotes bar open, bar close, or historical availability. The current public Kaggle dataset metadata reports version 759, whereas the local snapshot claims version 745; the local SHA identifies the current bytes but the exact v745-to-file mapping was not independently corroborated from version-specific metadata. The current file scan found zero null cells, invalid OHLC rows, duplicate/nonpositive timestamp steps, or non-60-second steps. However, `data_intake_manifest.json` claims a verified 60-second bar-close/PIT contract while `provenance.template.json` records timestamp role and `available_time` as unverified. The older `G0_FOUNDATION_INTEGRITY.md` says the same semantics were not verified; `g0_closure_report.md` later declares them passed without source-level evidence. The CSV has no `available_time` column. | Kaggle declares CC BY-SA 4.0, and the intake/rights log records user approval for research. The earlier G0 report still calls upstream rights and ShareAlike compatibility unresolved. These records support that research approval was recorded, but conflict on whether the full source-rights and use-scope review was completed. | **Not accepted.** Resolve the documented rights-record conflict and verify the timestamp label and historical availability rule from primary source evidence. Do not infer bar-close time from monotonicity or 60-second cadence. |
| Coinbase Exchange BTC-USD 15-minute parquet | `data/raw/coinbase_15m.parquet`; 464,798 bytes; SHA-256 `7fcd61d21a995c251688e6ae687fa1678f0bec7bfb5cf08ea87f5ebb6f9d1091`; 9,000 rows; 2026-07-21 20:15 UTC through 2026-10-23 14:00 UTC | Coinbase Exchange identifies candle `time` as the bucket start. The local manifest reports a single continuous segment. The adapter stores that bucket-start timestamp as `timestamp` / `epoch_time`, does not persist an explicit `available_time`, and labels the last candle's bucket start as `last_completed_candle_utc`. The returned current/forming bucket is filtered, but this is not a persisted, auditable availability-time contract. This 15-minute dataset cannot supply the preregistered 1-minute path-resolution input. | Coinbase API documentation refers users to Market Data Terms of Use. No evidence in the local manifest establishes that the relevant permitted-use scope was reviewed and approved for this snapshot. No approval is inferred. | **Not accepted.** Resolve permitted-use scope and correct/verify availability-time metadata before any reuse; it also does not meet the 1-minute path requirement. |
| Binance BTCUSDT hourly parquet used by existing ingestion/tournament paths | Existing `data/raw/ohlcv.parquet`; no V31.1 frozen manifest was created. The ingestion source identifies Binance BTCUSDT and assigns availability as the candle timestamp plus one hour. | V12 labels the dataset as Coinbase BTC-USD, so venue, symbol, and product do not agree. Existing manifests are not a current, dataset-specific acceptance record for the exact bytes and intended study. Hourly bars do not meet the 1-minute path requirement. | No dataset-specific rights/use acceptance for this V31.1 study was established. | **Not accepted.** Do not substitute this data for either Coinbase BTC-USD or Bitstamp BTC/USD. |
| Funding-rate data | Multiple local records / code paths | A funding value is not sufficient provenance: a timestamped historical series and a verified join convention to the selected venue, instrument, and holding interval were not established for this gate. | Not independently cleared for the proposed join/use. | **Not accepted as an input.** Do not use a configured assumed funding rate as historical funding evidence. |

## Bitstamp snapshot verification

The local file's SHA-256, byte size, row count, timestamp range, and structural checks were recomputed read-only for this audit. Result:

```text
bytes=393952273
sha256=1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287
rows=7766111
null_cells=0
invalid_ohlc_rows=0
duplicate_timestamps=0
nonpositive_steps=0
non_60s_steps=0
```

This establishes byte identity and regular observed spacing in the present file. It does **not** establish whether a timestamp denotes a bar's open, close, or source publication time; whether a completed bar was available at the claimed decision time; whether missing ticks were omitted upstream; or whether a hypothetical order could have filled at a barrier. The intake manifest's `VERIFIED_60S_BAR_CLOSE` and `VERIFIED` PIT labels are not reconciled with the still-unverified provenance template and original G0 record. The later G0 closure's `PASS` statement is preserved as historical evidence, not treated as primary-source proof.

The use record is also conflicting: the intake and rights checklist record user approval for research under Kaggle's declared CC BY-SA 4.0 license, while the earlier G0 audit says upstream rights and ShareAlike compatibility remain for review. Kaggle's current public metadata reports dataset version 759, while the local snapshot claims version 745; the local hash identifies the current bytes but was not independently mapped to that exact historic version. The publisher's updater confirms a Bitstamp source and 60-second request interval, but carries the raw timestamp without defining its bar boundary. This audit does not revoke the recorded approval or make a legal determination; it records that the repository does not contain a reconciled, auditable resolution of the conflict and does not extend approval to redistribution or commercial product use.

## Coinbase timestamp and use limitations

Coinbase's public candle documentation describes the candle `time` as the start of its bucket. Thus the manifest's `last_completed_candle_utc` value of `2026-10-23T14:00:00Z` identifies the bucket start, not the time at which that 15-minute candle became complete. The adapter's current-bucket exclusion is useful but does not record an availability timestamp per persisted row. The data is also too coarse for the V1 entry preregistration's 1-minute path resolver.

## Sources checked

- Kaggle dataset listing: <https://www.kaggle.com/datasets/mczielinski/bitcoin-historical-data>
- Kaggle dataset API metadata (current public metadata reports version 759 and CC BY-SA 4.0): <https://www.kaggle.com/api/v1/datasets/view/mczielinski/bitcoin-historical-data>
- Publisher automation repository: <https://github.com/mczielinski/kaggle-bitcoin>. Its updater fetches Bitstamp OHLC with `step=60` and passes the API timestamp field into the dataset; it does not establish bar boundary or historical availability semantics.
- Coinbase Exchange product candles reference: <https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproductcandles>
- Coinbase Exchange Market Data Terms of Use, linked from its API documentation: <https://www.coinbase.com/legal/market_data>
- Repository contracts: `research/entry_tp_sl/data_intake_manifest.json`, `research/entry_tp_sl/provenance.template.json`, `research/entry_tp_sl/dataset_manifest.template.json`, `research/entry_tp_sl/data_model_rights_checklist.md`, `research/entry_tp_sl/G0_FOUNDATION_INTEGRITY.md`, `research/entry_tp_sl/g0_closure_report.md`, and `research/entry_tp_sl/DATA_INTAKE_BLOCKERS.md`.
- Local Coinbase source mapping: `engine/coinbase_15m_adapter.py`; Binance source mapping: `data/ingest_real_historical.py`; V12 instrument label: `research/v12_strategy_tournament_engine.py`.

## Gate A disposition and required evidence

**Gate A: BLOCKED.** Do not create a frozen manifest or begin performance work until one named dataset has all of the following:

1. A byte-level snapshot identity and a reconciled venue, product, symbol, and granularity.
2. Primary-source evidence defining the timestamp's event-time role and a deterministic, conservative `available_time` rule for every feature/path observation.
3. A reconciled record of the applicable license/terms and permitted use, restricted to the authorized research scope.
4. Verified coverage, duplicate, missing-bar, and OHLC policies appropriate to the frozen replay contract.
5. A manifest that is consistent with the data artifact and does not conflict with the historical provenance records.

Until those conditions are met, the next step is provenance resolution, not replay implementation, cost tuning, or strategy evaluation.
