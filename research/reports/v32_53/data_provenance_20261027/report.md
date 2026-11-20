# V32.53 — Appended OHLCV Candle Provenance

**Audit ID:** `v32.53-coinbase-btc-usd-hourly-append-20261027`  
**Captured:** `2026-10-27T10:48:20.719548Z`  
**Scope:** The 56 rows present in `data/raw/ohlcv.parquet` after the historical `2026-10-24T08:00:00Z` endpoint.

## Result

**The 56 appended candles are independently verified against the official Coinbase Exchange public REST API for spot `BTC-USD` hourly candles.** The API returned exactly the expected 56 unique timestamps from `2026-10-24T09:00:00Z` through `2026-10-26T16:00:00Z`, inclusive. The local and source timestamp sets were identical, and all 280 numeric OHLCV values (five fields across 56 rows) matched exactly. No parquet was restored or rewritten.

This confirms the candle values and their market/timeframe identity at capture time. It does **not** establish who appended them to the local parquet, when that local write occurred, or the authorization/process that performed it. The wider integrity incident and V32.53 release remain **BLOCKED** pending the other gates.

## Source and reproducible evidence

- **Venue / market:** Coinbase Exchange spot, product `BTC-USD`
- **Granularity:** 3,600 seconds (one hour)
- **Exact request:** `https://api.exchange.coinbase.com/products/BTC-USD/candles?start=2026-10-24T09:00:00Z&end=2026-10-26T16:00:00Z&granularity=3600`
- **HTTP result:** `200`, `application/json; charset=utf-8`
- **API response:** [coinbase_btc_usd_candles_20261024T090000Z_20261026T160000Z.json](./coinbase_btc_usd_candles_20261024T090000Z_20261026T160000Z.json), 3,363 bytes, SHA-256 `da7ff9bb7485db7c731f04484800736bb47af7bf1978e5b923549ccb4f64ab5f`
- **Machine-readable validation:** [validation.json](./validation.json)

To reproduce the comparison from the archived response, interpret each Coinbase row as `[epoch_seconds, low, high, open, close, volume]`; convert the epoch to a UTC candle-open timestamp; select the local rows in the inclusive interval above; and compare timestamp sets and all five numeric fields after mapping into the local `[timestamp, open, high, low, close, volume]` schema. The archived response hash pins the exact source payload used for this result.

## Integrity checks

- Local parquet SHA-256 at validation: `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f`.
- All 56 local rows were timezone-aware UTC. All `available_time` values were timezone-aware UTC and exactly one hour after the candle-open timestamp.
- The 56 rows had finite OHLCV values, valid OHLC bounds, and non-negative volume.
- The full 42,233-row primary series was strictly increasing, had no duplicate timestamps, and had no non-hourly steps; its UTC range was `2022-01-01T00:00:00Z`–`2026-10-26T16:00:00Z`.
- SHA-256 values for the primary parquet, both backups, and three prospective ledgers matched the V32.52 preflight values before and after this read-only comparison. Their hashes are recorded in `validation.json`.
- No canonical data, backup, ledger, or prior report was changed. The only new files are this report and the archived evidence in this directory.

## Remaining limits and governed decision

The official API comparison verifies the added candle content, but it does not explain the local append event or establish a chain of custody for the 42,177 earlier rows. Coinbase data can be revised or become unavailable later; the response body and digest are therefore retained here. The exact API response is evidence of data consistency, not a claim about a profitable trading strategy.

- **Research Experiment:** `INCONCLUSIVE`
- **Prospective Evidence:** `COLLECTING` (no new prospective evidence was generated or counted)
- **Model Authorization:** `OFFLINE_RESEARCH_ONLY`
- **Live Trading:** `DISABLED`
- **Overall V32.53:** `BLOCKED` — authorization consistency, failure disposition, browser QA, performance, and cleanup gates remain outstanding.
