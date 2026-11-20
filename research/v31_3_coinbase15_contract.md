# BTCognitive V31.3 — Coinbase BTC-USD 15m Isolated Research Contract

**Status:** `CONTRACT DEFINED — VALIDATION BLOCKED`  
**Scope:** Separate Coinbase BTC-USD 15-minute contextual research only. No replay, strategy evaluation, performance claim, or production activation.

## 1. Contract identity

- **Contract ID:** `COINBASE-BTC-USD-15M-ISOLATED-V1`
- **Provider/venue:** Coinbase Exchange REST API
- **Instrument:** BTC-USD
- **Granularity:** 15 minutes (900 seconds)
- **Artifact path:** `data/raw/coinbase_15m.parquet`
- **Artifact size:** 464,798 bytes
- **SHA-256:** `7fcd61d21a995c251688e6ae687fa1678f0bec7bfb5cf08ea87f5ebb6f9d1091`
- **Manifest path:** `data/raw/coinbase_15m_manifest.json`
- **Manifest status:** `VALIDATED`
- **Row count:** 9000
- **First candle:** `2026-07-21T20:15:00Z`
- **Last completed candle:** `2026-10-23T14:00:00Z`
- **Timezone:** UTC
- **Timestamp convention:** bucket-start timestamp aligned to 900-second intervals
- **Availability rule:** completed 15-minute candle only; the currently forming bucket is excluded
- **Rights status:** `UNVERIFIED` — no repo-local legal-use record or terms approval for this exact artifact is present

## 2. Verified source evidence in repo

The artifact is directly identified by the adapter and the local manifest:

- `engine/coinbase_15m_adapter.py` defines the official Coinbase REST endpoint and verifies `granularity=900` and `time` as the bucket-start value.
- `data/raw/coinbase_15m_manifest.json` declares `instrument: "BTC-USD"`, `granularity_seconds: 900`, `gap_count: 0`, and `segment_count: 1`.
- The local parquet file is validated by `validate_and_segment_candles()` in the adapter, which rejects non-900s timestamps, duplicates, malformed OHLC, and partial forming candles.

## 3. Research scope and explicit exclusions

This contract is intentionally limited to a separate, exploratory 15-minute contextual study and excludes all of the following from the active scope:

- Bitstamp 1-minute data path
- Binance hourly data path
- V12 tournament assumptions
- 1-minute TP/SL ordering claims
- exact intrabar fill-path logic
- profitability, execution-quality, or performance claims not established by a future approved study
- any production or live-trading activation

## 4. Contract assumptions and open blockers

### Assumed for isolated exploratory use
- The local data is a completed 15-minute candle dataset with a bucket-start timestamp, not a 1-minute intrabar feed.
- Availability is defined by the observation that the current in-progress 15-minute bucket is excluded before it becomes a completed candle.

### Unresolved / not claimed
- legal permission for the exact artifact in this repository is not proven by this task;
- the file is not a substitute for the Bitstamp 1-minute signal path;
- the file is not proof of any strategy success or execution quality.

## 5. Contract decision

This contract is isolated and intentionally non-authoritative. It can be used only for a separate, documented 15-minute context study after the remaining provenance/policy gate is resolved.
