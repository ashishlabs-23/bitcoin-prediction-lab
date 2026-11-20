# BTCognitive V36.1 — Data and Model Lineage

## Findings

| Asset | Path/identity | Read-only finding | Decision |
|---|---|---|---|
| Bitstamp BTC/USD 1h snapshot | `data/providers/bitstamp/BTCUSD_1h.parquet` | 1,000 rows; SHA-256 `d64cd2591b4cc5c5a6328785b1722ec5f8e01b78f30dee7f1dc7dff583e7fc54`; matches `provenance.json`. Prior checks: ordered unique hourly timestamps, no gaps, `available_time = timestamp + 1h`, finite/valid OHLC and nonnegative volume. Latest close 2026-11-03 15:00 UTC. | Verified local file and own manifest; historical/stale for current-market decision. Original raw response is absent, so its digest cannot be independently recomputed. |
| `data/raw/ohlcv.parquet` | SHA-256 `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057` | Current raw file hash read-only. | Do not assume it is the frozen HAR-RS-DOW training input. |
| HAR-RS-DOW frozen training identity | `experiments/results/freeze/har_rs_dow_v1_baseline_manifest.json`; training data hash `689390a737402fd2ea4ec78d3dcde2eaca2a34617d6bd4f002de87c65d8a2697` | Manifest preserves a hash different from the current `data/raw/ohlcv.parquet`; artifact/model remains in research lifecycle. | Lineage mismatch unresolved. Do not replace data, edit manifest, or promote challenger. |
| Coinbase verified V1 parquet | `b81688644812276856ede9b9c38db21aaccba56387b284112a3d0175685bf5cf`; 33,424 rows, 3 known gaps | Separate acquisition history and file identity. | Not a substitute for Bitstamp or raw parquet. |
| Coinbase V2/V3 parquet | Both `172a21c99a67b91198988efd7dfdf4a26035701dbb05bdd2d213b481ad6a6360`; 42,237 rows | Matching hashes do not imply identity with V1, Bitstamp, or the HAR-RS-DOW frozen training data. | Keep dataset lineage separate. |
| Standard HAR | Authoritative registry entry points to absent artifact/placeholder hash | Exact model bytes and training provenance not recovered. | Standard HAR performance `NOT_ESTABLISHED`; do not run an approximate/retrained replacement and call it registered Standard HAR. |
| Funding | `data/raw/funding.parquet` | 375 observations ending 2026-05-05. | Historical/stale auxiliary source; not contemporaneous with Bitstamp snapshot absent verified PIT join. |
| Open interest | `data/raw/oi.parquet` | 3,000 observations ending 2026-05-05. | Same restriction; unavailable in current snapshot contract. |
| On-chain | `data/raw/onchain.parquet` | 30 records ending 2026-10-30. | Separate, sparse/stale source; not an hourly candle feature absent verified semantics. |
| Order book/liquidations | No corresponding event stream in inspected Bitstamp snapshot | No sequence-level book updates or liquidation events. | `DATA_UNAVAILABLE`; no OHLCV-derived proxy. |

## Reconciliation

The V36.0 Bitstamp cache check established internal Parquet/provenance agreement; it did not establish that the raw response bytes are retained. The previously reported mismatch refers to a distinct relationship: current `data/raw/ohlcv.parquet` hash versus the frozen HAR-RS-DOW manifest training hash. Current raw hash `ba06…4057` is not frozen manifest hash `6893…2697`; no evidence reviewed justifies replacing either. Coinbase datasets are separate snapshots with differing row counts/gap descriptions and hashes.

The Standard HAR registry cannot be reconciled to an exact inference artifact because the expected artifact is absent and its hash is a placeholder. Therefore no Standard HAR forecast run, accuracy measurement, or artifact substitution is justified. HAR-RS-DOW stays unpromoted and its lineage discrepancy remains unresolved.

Prior [V35_2 research reports](./V35_2_VOLATILITY_MODEL_RESEARCH.md) recorded historical Standard HAR results. This V36.1 report does not erase or silently revise those reports; it records that the exact currently registered artifact and training lineage were not recovered for this inspection, so the historical reported performance cannot be freshly reproduced here. Treat it as prior retrospective evidence, not new confirmation.

## Integrity and safety boundary

No dataset, manifest, hash, model artifact, prospective ledger, or database was changed. The numbers above are read-only findings from existing files; database and historical-ledger integrity was not audited. Historical replay can use only the Bitstamp file's local SHA-verified bytes, but no engine was run in V36.1. The raw-response digest remains unverifiable.
