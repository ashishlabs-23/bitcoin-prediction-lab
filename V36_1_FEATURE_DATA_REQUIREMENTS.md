# BTCognitive V36.1 — Feature Data Requirements

## Source contract

Each feature row must declare: instrument/symbol; venue/source and rights; event timestamp; availability/publication timestamp; timezone; interval; complete/closed status; units; raw and normalized hash; expected coverage; gap/duplicate rules; maximum age; transformation version; and failure code. Causality requires `feature_available_time <= decision_time`. A missing stream must return `DATA_UNAVAILABLE`, not a neutral synthetic measurement.

## Data matrix

| Feature group | Required data | Current evidence | Eligibility and failure behavior |
|---|---|---|---|
| Hourly OHLCV state/HAR candidates | BTC/USD closed hourly candles with event/availability timestamps; source and hash | Verified Bitstamp local snapshot: 1,000 rows, SHA-256 `d64cd2591b4cc5c5a6328785b1722ec5f8e01b78f30dee7f1dc7dff583e7fc54`; continuous and structurally valid per prior read-only inspection; last close 2026-11-03 15:00 UTC | Historical data only. Current freshness policy remains unchanged. Replay must label `HISTORICAL` and `STALE_FOR_CURRENT_MARKET`. Raw response absent, so raw-response digest cannot be recomputed. |
| Standard HAR | Exact registry artifact, exact training dataset bytes/hash, target definition, model code/version, training cutoff, forecast origin, dependencies/environment | Registry artifact absent and hash placeholder | `MODEL_UNAVAILABLE`/`PROVENANCE_FAILURE`; no forecast accuracy claim until exact artifact and lineage recover. |
| HAR-RS-DOW | Frozen artifact plus exact frozen training data and manifest | Manifest training hash `689390a737402fd2ea4ec78d3dcde2eaca2a34617d6bd4f002de87c65d8a2697`; current `data/raw/ohlcv.parquet` hash `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057` | Do not substitute datasets. Preserve unpromoted lifecycle; resolve mismatch before evaluating this snapshot as its training lineage. |
| Coinbase historical OHLCV comparisons | Exact dataset/version plus source/acquisition period and gap treatment | V1 parquet SHA `b81688644812276856ede9b9c38db21aaccba56387b284112a3d0175685bf5cf`, 33,424 rows, 3 known gaps; V2 and V3 share SHA `172a21c99a67b91198988efd7dfdf4a26035701dbb05bdd2d213b481ad6a6360`, 42,237 rows | Separate lineage; do not silently substitute for Bitstamp or raw parquet. |
| 15m trend/setup/volatility | Closed BTCUSD 15m OHLCV with UTC and availability times; at least module-specific history | Not present in verified Bitstamp 1h snapshot | `DATA_UNAVAILABLE` for this replay; do not resample 1h bars into synthetic 15m candles. |
| Barrier outcomes and trade probability labels | Frozen 15m decision bars; next 1m open fill; 1m path through 120/240m horizon; frozen cost and ambiguity contract | Frozen research contracts exist; Bitstamp snapshot has hourly candles only | No labels or 3-class probabilities from current snapshot. Never infer intrabar order from hourly high/low. |
| Order book / microstructure | Venue-specific L2 snapshots and ordered updates; heartbeat/sequence-gap detection; matches/trades; timestamps and units | No order-book event stream in Bitstamp snapshot | `DATA_UNAVAILABLE`; spread/OFI/imbalance/CVD/liquidity cannot be reconstructed from OHLCV. |
| Funding / open interest | Source-specific values, event and publication time, instrument/venue, units, corrections, cadence | `data/raw/funding.parquet`: 375 observations ending 2026-05-05; `oi.parquet`: 3,000 ending 2026-05-05 | Historical/stale, separate from snapshot. Require PIT as-of join and provenance; do not report as current or join without contract verification. |
| Liquidations | Timestamped venue/aggregator liquidation events, contract units and coverage | No eligible data source evidenced | `DATA_UNAVAILABLE`; no proxy from candle volume/range. |
| On-chain | Chain/source timestamp and publication latency; metric definitions and revisions | `data/raw/onchain.parquet`: 30 records ending 2026-10-30 | Stale and separate; not an hourly market observation. Use only after source semantics and point-in-time availability are verified. |
| Sentiment/macro | Permissioned original source, publication timestamps, versioned transforms and missingness | Configurable references exist in pipeline; current source freshness/provenance not established | `DATA_UNAVAILABLE` unless source and record are verifiable. Do not fill missing values with neutral scores. |
| Cost/fees/spread/slippage | Venue/instrument/taker role, fee schedule date, spread or trade/book evidence, impact/latency assumptions | Frozen entry contract has BASE 35 bps and CONSERVATIVE 65 bps assumptions for its research design | Clearly label assumptions and sensitivity. These are not measured current costs or fills. |
| Prospective forecast/outcome ledger | Frozen forecast identity, issue time, maturity time, mature outcome source and append-only integrity | Protected existing database/ledgers; no integrity verification in this read-only inventory | Do not read-modify or write as part of replay; no protocol or frozen record changes. |

## Snapshot quality, lineage, and freshness

The local Bitstamp file is internally consistent with its own provenance manifest; its Parquet SHA-256 is `d64cd2591b4cc5c5a6328785b1722ec5f8e01b78f30dee7f1dc7dff583e7fc54`. The inspected checks found ordered unique timestamps, continuous hourly spacing, `available_time = timestamp + 1h`, finite/valid OHLC geometry, and nonnegative volume. These are file-contract checks, not a reconstruction of the original raw HTTP response. The snapshot is stale under the existing two-hour current-market freshness policy. Do not weaken that policy.

`data/raw/ohlcv.parquet` and the Coinbase snapshots represent distinct files and histories. The raw OHLCV hash does not equal the HAR-RS-DOW frozen training hash; comparisons and manifests must retain those distinctions. The Standard HAR registry artifact is not recovered, so Standard HAR performance stays `NOT_ESTABLISHED`.

## Failure contract

Reject or explicitly mark unavailable on: provider/network attempt in replay; source/hash mismatch; wrong symbol/venue; invalid or missing timestamps/timezone; future availability time; forming candles; stale-for-current data; duplicate/missing intervals; invalid OHLC geometry; non-finite fields; unverified model identity; missing auxiliary stream; incompatible cadence; incomplete execution path; and database write attempts. Do not substitute a different provider or fabricate fields.
