# BTCognitive V31.3 — Coinbase BTC-USD 15m Validation Report

**Status:** `CONTRACT DEFINED — VALIDATION BLOCKED`  
**Scope:** Direct validation of the local Coinbase BTC-USD 15m artifact only.

## 1. Actual artifact verified

- **Path:** `data/raw/coinbase_15m.parquet`
- **Size:** 464,798 bytes
- **SHA-256:** `7fcd61d21a995c251688e6ae687fa1678f0bec7bfb5cf08ea87f5ebb6f9d1091`
- **Manifest:** `data/raw/coinbase_15m_manifest.json`
- **Rows:** 9000
- **Timestamp span:** `2026-07-21 20:15:00+00:00` to `2026-10-23 14:00:00+00:00`
- **Timezone:** UTC
- **Interval consistency:** all observed steps are 15 minutes
- **Duplicates:** 0
- **Nulls:** 0 across all fields
- **Gaps:** 0

## 2. Evidence used

- `engine/coinbase_15m_adapter.py`
- `data/raw/coinbase_15m_manifest.json`
- local parquet inspection via Pandas/pyarrow
- repository evidence in `research/v31_2_blocker_resolution.md`

## 3. Gate status

| Gate | Status | Evidence | Unresolved question | Next action |
|---|---|---|---|---|
| C1 — Artifact identity | PASS | File path, size, and SHA-256 match the manifest; both are consistent with the on-disk parquet. | None in the local artifact. | Keep the hash and file path frozen for future reference. |
| C2 — Venue/instrument identity | PASS | Adapter and manifest both identify Coinbase Exchange and `BTC-USD`; local data uses `BTC-USD` columns and `900`-second candlesticks. | None for the local source identity. | Keep this source isolated from other venue/instrument sources. |
| C3 — Timestamp semantics | PASS | Adapter response uses `[time, low, high, open, close, volume]`, validation checks `t % 900 == 0`, and the parquet stores UTC timestamps on 15-minute boundaries. | Whether the source treats bucket start as an event-time or availability-time convention needs source-document confirmation if used beyond local context. | Treat the timestamp as bucket-start, not intrabar time, in the isolated contract. |
| C4 — Availability semantics | PASS (contractually defined for isolated use) | Adapter explicitly excludes the forming bucket and only keeps completed 15-minute candles. | Not a legal or contract-proof statement from the exchange terms; it is a local validation policy. | Keep this rule explicit in any future exploratory study and do not generalize it to 1-minute TP/SL or fill modeling. |
| C5 — Data integrity | PASS | 9000 valid rows, 0 duplicates, 0 missing values, 0 gaps, and a consistent 15-minute cadence. | This validates the local artifact; it does not prove the feed is complete in all historical episodes or legally permitted for downstream use. | Preserve the data as a bounded, local artifact and document the limitations. |
| C6 — Provenance and permitted use | UNVERIFIED | The repo contains no legal-use or licensing record for the exact local artifact. Source is identified as Coinbase Exchange, but rights/permission are not proven here. | No evidence in repo proving acceptable research-use permission for this exact artifact. | Obtain a written source or terms record before any future non-exploratory use. |
| C7 — Scope isolation | PASS | The isolated contract explicitly excludes Bitstamp 1-minute, Binance hourly, and V12 tournament assumptions. | None for the isolated path itself. | Keep the contract separate and do not merge with other source paths. |
| C8 — Research limitations | PASS | The contract states prohibited claims: 1-minute TP/SL ordering, exact intrabar path, fill quality, profitability, and execution claims unsupported by the 15-minute OHLCV artifact. | Future work must still pass its own approval gate. | Maintain this scope boundary and do not widen it. |

## 4. Decision

**`CONTRACT DEFINED — VALIDATION BLOCKED`**

This artifact is a coherent Coinbase BTC-USD 15-minute local dataset with a clear bucket-start timestamp and completed-candle filter. That is enough to define a separate 15-minute contextual contract. It is not enough to declare the source qualified for broader research because the legal-use and provenance status remains unresolved.

## 5. Remaining blockers

1. **Rights / permitted-use proof is missing**  
   Evidence needed: a written source terms or permission statement for the exact local artifact used in this repo.

2. **No future authorized study is in place**  
   Evidence needed: a separate, human-reviewed study contract defining the exact 15-minute research question and the permanent exclusions.

3. **No claim beyond contextual 15-minute analysis is approved**  
   Evidence needed: a future, separate approval before any strategy or replay work is considered.

## 6. Final recommendation

The Coinbase BTC-USD 15-minute artifact is suitable for a narrow, isolated, contextual research contract only. It must remain separate from Bitstamp, Binance, and V12 assumptions. No replay, strategy evaluation, or performance claim should proceed until the provenance/permission gate is resolved and a future human-approved study scope is specified.
