# V37.3 Workstream 1 — Data Qualification

**Disposition:** `INCONCLUSIVE` for research admission. This was a bounded source/data qualification only, not a model or performance evaluation.

**Decision time:** 2026-11-04

**Repository baseline:** `milestone/v35.3-critical-remediation` at `25d483f4c3646661b57311de9d0b53d2be881adb`; the worktree already contained unrelated modifications. This work changed only this report in the repository.

## Status vocabulary

- **VERIFIED** — directly checked in this task, limited to the stated observation.
- **SOURCE_CORROBORATED_NOT_PROVEN** — a local file fingerprint agrees with a local manifest/provenance record; this does not authenticate the original source.
- **INFERRED** — a transparent calculation or interpretation based on stated assumptions.
- **UNVERIFIED** — unresolved source, rights, timestamp, or other provenance claim.
- **UNAVAILABLE** — required evidence could not be obtained in this task.

## One-time Bitstamp BTC/USD minute request

Exactly one unauthenticated, read-only market-data request was sent:

```text
GET https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=60&limit=10&exclude_current_candle=true
```

No credentials, account/private APIs, other market-data providers, retries, or redirect-following were used. Retrieval began at **2026-11-04T14:04:58.561Z** and completed at **2026-11-04T14:05:00.100Z**. **HTTP 200** returned pair `BTC/USD` and **10 candle records**. The response was requested with current-candle exclusion; the first returned timestamp was **2026-11-04T13:51:00Z**, and the last was **2026-11-04T14:00:00Z**.

### Response checks — VERIFIED

- All 10 records have finite numeric open, high, low, close, and volume values.
- Every record passes `high >= max(open, close)`, `low <= min(open, close)`, `high >= low`, and `volume >= 0`.
- Returned timestamps are strictly increasing, with no duplicates.
- There are no missing one-minute timestamps **within** the returned window (13:51 through 14:00 inclusive).
- By response completion, the four latest expected completed starts at **14:01, 14:02, 14:03, and 14:04Z** were not returned. At request start, 14:04 was still forming, so only 14:01–14:03 were expected complete. This describes this response, not proof those candles are absent from Bitstamp’s full history.

### Freshness — INFERRED from the response timestamps

The final returned timestamp is **14:00:00Z**. Assuming it denotes the start of a one-minute candle, that candle closed at **14:01:00Z**. At request start it was **238.561 seconds past that close**; at response completion it was **240.1 seconds past close**. The GET straddled the 14:05 minute boundary: at request start the latest expected completed start was **14:03:00Z**, with 14:01–14:03 not returned; at response completion it was **14:04:00Z**, with 14:01–14:04 not returned. The endpoint does not expose its server-side snapshot time, so both as-of times are reported. This response was about four minutes stale; the cause is unknown.

## Official Bitstamp legal/data-use lookup

This was a separate legal/docs lookup, not another market-data request. A request to the official `https://www.bitstamp.net/legal/` page failed at the transport layer. A separate GET to the official `https://www.bitstamp.net/terms-of-use/` returned HTTP 200 but only a 212-byte Incapsula challenge/interstitial, not substantive terms. **Official commercial data-license terms: UNAVAILABLE.** The local Bitstamp provenance files’ “Private Research Scope” labels are repository assertions, not a verified commercial license. No conclusion that commercial reuse is permitted is made.

## Local lineage and fingerprint review

Only the named minute and hourly files and their local lineage records were fingerprinted or inspected. SHA-256 matches establish local byte identity against those records, not original-source authenticity.

| Local object | Current fingerprint / recorded metadata | Local corroboration and disposition |
|---|---|---|
| `data/raw/btcusd_1-min_data.csv` | 393,952,273 bytes; SHA-256 `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`; intake metadata lists 7,766,111 rows through 2026-10-07T03:11:00Z. | Current hash matches `data_intake_manifest.json`, `contract_freeze_manifest.json`, and `6B_implementation_manifest.json`: **SOURCE_CORROBORATED_NOT_PROVEN** for the local snapshot. The intake manifest claims Kaggle v745 / Bitstamp and a 60-second bar-close contract, while the candidate provenance and dataset templates explicitly leave source/timestamp role unverified and rights review required. Original source, licensing, timestamp role, and point-in-time availability remain **UNVERIFIED**. No rows were parsed for selection or research. |
| Coinbase hourly V1, `data/research/coinbase_btc_usd_hourly_v1/coinbase_hourly.parquet` | 1,713,424 bytes; SHA-256 `b81688644812276856ede9b9c38db21aaccba56387b284112a3d0175685bf5cf`; manifest lists 33,424 rows, 2023-01-01 through 2026-10-25 04:00Z, with three gaps. | Current hash matches `coinbase_hourly_manifest.json`: **SOURCE_CORROBORATED_NOT_PROVEN**. The manifest records acquisition from Coinbase’s public BTC-USD candles endpoint. This task made no Coinbase request; original source is not independently authenticated here. |
| Coinbase hourly verified V2 and V3, `data/research/coinbase_btc_usd_hourly_verified_v2/` and `_v3/` | Both current Parquet files are 2,291,318 bytes with identical SHA-256 `172a21c99a67b91198988efd7dfdf4a26035701dbb05bdd2d213b481ad6a6360`. Local validation records 42,237 rows through 2026-10-27 09:00Z and 13 missing hourly timestamps in three intervals. | The hash matches both acquisition manifests: **SOURCE_CORROBORATED_NOT_PROVEN** for the stored artifact. V2 and V3 having the same hash is identity of content, not independent evidence. Local Coinbase comparison records provide same-source consistency evidence against V1 on shared rows, but do not prove original provenance or license rights. |
| Bitstamp hourly current snapshot, `data/providers/bitstamp/BTCUSD_1h.parquet` | 56,271 bytes; SHA-256 `d64cd2591b4cc5c5a6328785b1722ec5f8e01b78f30dee7f1dc7dff583e7fc54`; local provenance lists 1,000 rows, 2026-09-22 23:00Z through 2026-11-03 14:00Z (close 15:00Z), retrieval at 2026-11-03 15:08Z. | Current hash matches `data/providers/bitstamp/provenance.json`: **SOURCE_CORROBORATED_NOT_PROVEN**. Its recorded raw-payload hash was not independently rechecked against a raw payload in this task. At the one-time request completion, its latest recorded hourly close was about 23 hours old. |
| Bitstamp expansion snapshots `BTCUSD_1h_v34_expanded.parquet` and `BTCUSD_1h_v34_2_multiyear.parquet` | Current hashes `9e8d92a2db78a5c71737146713541c3db5f27d398684114f09d5db3a4493ec81` and `811c9704629d3b735643c0d931ad1998cf0604e9dd96b9790aaf1241ee807436`, respectively. | Each current hash matches its adjacent local provenance record: **SOURCE_CORROBORATED_NOT_PROVEN**. Their declared Bitstamp lineage and private-research scope remain local claims; official licensing was not established. |

No Coinbase and Bitstamp series were concatenated or compared by candle value in this task. No original-source claim is upgraded to `VERIFIED`. No holdout observations were opened or used for model selection; no model selection, replay, training, or performance calculation was performed.

## Isolated QA outputs

The raw response and structured checks are outside the repository in:

```text
C:\Users\Ashish\.copilot\session-state\51eedde1-236e-4970-84a5-a1b2daff43ad\files\v37_3_data_qualification\
```

- `bitstamp_ohlc_raw_response.json` — raw market response; SHA-256 `e5ccde2897026e9d6c826e8df17e31ab83b1e589f9bc499c71241eac9d0bfd6a`
- `bitstamp_ohlc_structured_qa.json` — request metadata, parsed rows, invariants, ordering, duplicates, freshness at request start and response completion, and expected timestamps; SHA-256 `19fefcb9bc4af91cdbe5e175757964618193be1df0c124dd3b69332f95ee2088`
- `official_terms_lookup_status.json` and `official_terms_lookup_raw.html` — separate legal/docs retrieval status and the non-substantive interstitial.

## Governed decision

1. **Research Experiment:** `INCONCLUSIVE` — data qualification only; no experiment was run.
2. **Prospective Evidence:** `NOT_STARTED` for this workstream — no prospective observation was appended or resolved.
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`.
4. **Live Trading:** `DISABLED`.

## Dated addendum — cross-source hourly overlap (2026-11-04)

This follow-up read only timestamp, available-time, and OHLCV columns from the named Coinbase V2/V3 and Bitstamp hourly Parquet files. It aligned rows on exact UTC hourly timestamps and computed aggregate comparisons only. No raw candle values are reproduced here; no rows were used for selection, outcome analysis, model fitting, or performance evaluation.

Coinbase V2 and V3 each contain 42,237 rows and have the same Parquet SHA-256 (`172a21c99a67b91198988efd7dfdf4a26035701dbb05bdd2d213b481ad6a6360`); the row-level fields were equal on all 42,237 shared timestamps. They are therefore one identical Coinbase data content for this comparison, not two independent cross-source checks.

Both locally recorded timestamp contracts identify UTC candle-open timestamps with availability one hour later. In the exact timestamp overlap:

- **827 matched hourly rows**, from **2026-09-22T23:00:00Z** through **2026-10-27T09:00:00Z**, with no missing hours inside the matched sequence.
- All 827 timestamps and corresponding `available_time` values aligned exactly; both files had `available_time = timestamp + 1 hour` on those rows.
- Both files store numeric OHLCV as float64; underlying exchange quote precision cannot be inferred from that storage type. On the 827 matched rows, exact (and two-decimal-rounded) OHLC equality counts were: open **2**, high **1**, low **2**, close **1**. No row had all four OHLC fields equal after cent rounding.
- Price levels are highly correlated, but not identical. Per-field median absolute Coinbase-to-Bitstamp differences were open **$5.07**, high **$11.08**, low **$12.25**, and close **$5.43**; median absolute difference as a percentage of Coinbase was **0.0061%**, **0.0132%**, **0.0147%**, and **0.0065%**, respectively. Pearson correlations were **0.99997–0.99999** by field. High price correlation is not source equivalence; the low exact/rounded match counts show venue-specific candle differences beyond simple decimal formatting.
- Volume was materially less similar: median absolute difference **105.8078** stored volume units, median absolute difference **73.42% of Coinbase volume**, Pearson correlation **0.83751**. Coinbase volume exceeded Bitstamp volume on **825/827** matched rows (Bitstamp was higher on 2). The comparison did not harmonize volume units beyond the datasets’ BTC/USD spot labels.

**Disposition:** the aligned overlap is `SOURCE_CORROBORATED_NOT_PROVEN` as a local cross-source comparison only. Exact timestamp alignment corroborates compatible hourly indexing; differing OHLC and volume values establish that the datasets are not interchangeable at the candle level. Correlation does not authenticate either original source, establish data correctness, explain venue/methodology differences, or resolve commercial rights. The main report’s earlier “not compared” statement records the state before this dated follow-up; it is not silently rewritten. Protected-file fingerprints were identical before and after the read-only comparison.
