# V32.54 — Independent Coinbase BTC-USD Hourly Dataset

**Dataset:** `coinbase_btc_usd_hourly_verified_v2`  
**Acquired:** `2026-10-27T10:57:17Z`–`2026-10-27T11:05:50Z`  
**Overall data disposition:** `ACQUIRED_WITH_REVIEW_REQUIRED`  
**Canonical data disposition:** unchanged; no restore, rewrite, interpolation, or substitution

## Acquisition and reproducibility

The dataset was independently fetched from Coinbase Exchange's public spot `BTC-USD` candle endpoint at one-hour granularity. Pagination used inclusive windows of at most 250 hourly timestamps per request, below Coinbase's 300-candle limit, with 0.35-second pacing between pages and bounded retries with exponential backoff for network errors, HTTP 429, and HTTP 5xx responses.

- Requested inclusive timestamp range: `2022-01-01T00:00:00Z`–`2026-10-27T09:00:00Z`.
- 169 successful HTTP 200 responses are archived in `raw_responses/`; the acquisition manifest records each exact URL, UTC request boundaries, capture time, response count, byte length, and SHA-256.
- Coinbase rows `[epoch_seconds, low, high, open, close, volume]` were mapped to UTC candle-open timestamps and the application OHLCV schema. `available_time` is derived as candle-open time plus one hour; it was not supplied by Coinbase.
- Dataset: [coinbase_btc_usd_hourly.parquet](./coinbase_btc_usd_hourly.parquet), SHA-256 `172a21c99a67b91198988efd7dfdf4a26035701dbb05bdd2d213b481ad6a6360`.
- Full request ledger and per-response digests: [acquisition_manifest.json](./acquisition_manifest.json).
- Row-level validation: [validation.json](./validation.json).
- Replay verification: [rebuild_verification.json](./rebuild_verification.json).
- Old-versus-new comparison: [comparison.json](./comparison.json); the complete shared-row OHLCV mismatch list is archived as compressed JSONL at [shared_value_mismatches.jsonl.gz](./shared_value_mismatches.jsonl.gz), SHA-256 `ed98cbccf845ee9788a53c9c186b990056ea80ba32793bd045fe38ae1855e2cd`.
- Independent acquisition cross-check: [cross_capture_comparison.json](./cross_capture_comparison.json).

Replay was run offline from the 169 archived raw response bodies. All response hashes and counts matched the manifest, and the reconstructed 42,237-row table matched the stored parquet values and SHA-256. The replay check is reproducible with:

```powershell
.\.venv_win\Scripts\python.exe research\data_acquisition\build_coinbase_hourly_verified_v2.py --verify-only
```

## Dataset validation

The 42,237 acquired rows are UTC, monotonic, and duplicate-free. All OHLCV values are finite; high/low relationships and nonnegative volume checks pass. No values were filled or substituted.

Coinbase returned no candle data for 13 timestamps in three intervals:

- `2023-03-04T18:00:00Z`–`2023-03-04T20:00:00Z` (3 hours)
- `2025-10-25T16:00:00Z`–`2025-10-25T20:00:00Z` (5 hours)
- `2026-05-08T02:00:00Z`–`2026-05-08T06:00:00Z` (5 hours)

These intervals remain missing. The data must not be treated as a fully continuous series or used by an analysis that assumes continuity across these boundaries without explicit gap-aware handling.

## Independent same-source capture check

The prior independently acquired Coinbase dataset V1 (captured 2026-10-25) has 33,424 timestamps, all of which overlap V2. Across all **33,424** shared timestamps, every open, high, low, close, and volume value matches exactly: **zero differences across 167,120 numeric values**. This supports repeatability of Coinbase's response values over the shared history for these two captures; it is not evidence that the underlying candles are error-free or that the research strategy has edge.

## Comparison with the existing primary parquet

The existing `data/raw/ohlcv.parquet` remains untouched. It has 42,233 rows through `2026-10-26T16:00:00Z`. Its timestamp set overlaps V2 at 42,220 timestamps; it contains the 13 timestamps within the Coinbase-missing intervals, and V2 contains 17 later hourly timestamps through `2026-10-27T09:00:00Z`.

Among shared timestamps, **204,236 of 211,100 OHLCV field values differ**:

| Field | Exact differences |
|---|---:|
| Open | 40,874 |
| High | 40,787 |
| Low | 40,799 |
| Close | 40,885 |
| Volume | 40,891 |

These are material value discrepancies, not silently classified as harmless rounding or Coinbase historical revisions. V1 and V2 agree exactly on their entire overlap, while the primary parquet does not match V2. The primary's original source, aggregation methodology, or alteration history remains unestablished. Do not treat its values as equivalent to the newly acquired Coinbase series, and do not overwrite or repair it using V2.

## Test and research boundary

The acquired V2 dataset is suitable as a **separate, source-pinned input for isolated exploratory software QA**, subject to its disclosed gaps and comparison discrepancies. It is not a replacement for the application's default dataset and is not yet a clean continuous research sample. Historical results from the primary parquet must be reproduced against V2 before they can be associated with the Coinbase V2 input. Exclude gap-spanning labels/windows or report them as unavailable; do not bridge missing candles.

- **Research Experiment:** `INCONCLUSIVE`
- **Prospective Evidence:** `COLLECTING` (this retrospective rebuild adds no prospective evidence)
- **Model Authorization:** `OFFLINE_RESEARCH_ONLY`
- **Live Trading:** `DISABLED`
- **V32.54:** `PARTIAL_PASS_BLOCKED` — independent acquisition, validation, and replay are complete; the primary-data discrepancy, authorization repair, full failure reconciliation, and application QA remain open.
