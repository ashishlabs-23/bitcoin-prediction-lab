# BTCognitive V34.5 — Historical Data Provider Audit: Tardis.dev Qualification & 4-Year Acquisition Plan

**Milestone:** BTCognitive V34.5 — Continuous Historical Data & Strategy Viability  
**Date:** 2026-11-03  
**Status:** COMPLETE / GOVERNED  
**Lead Author:** Agent 1 (Historical Data Provider Auditor)  
**Governed Assessment:** `CONTINUOUS_DATA_NOT_AVAILABLE` (In-repository / Public REST) | `PROVIDER_QUALIFIED_FOR_LICENSED_ACQUISITION` (Tardis.dev)

---

## 1. Executive Summary

Milestone V34.4 established that unauthenticated public REST endpoints on Bitstamp are throttled by Imperva Incapsula DDoS protection, leaving an unbridgeable **828.5-day gap (19,883 hours)** between the 2024 and 2026 local dataset segments. 

Agent 1 conducted a rigorous market qualification audit of **Tardis.dev** as a prospective institutional vendor for continuous Bitstamp BTC/USD historical tick and trade archives.

### Key Audit Findings
1. **Exchange Coverage & History:** Tardis.dev maintains continuous tick-level trade, quote, and L2 order book archives for Bitstamp Spot starting from **2019-03-30** (over 7.5 contiguous years of data).
2. **Exact Symbol Identity:** Bitstamp spot trades are captured under canonical symbol **`BTCUSD`** (`type: spot`). Perpetual futures are separately archived as **`BTCUSD-PERP`** (active since 2026-10-06).
3. **Capture Infrastructure:** Tardis captures Bitstamp via WebSocket (`wss://ws.bitstamp.net`) from GCP London (`europe-west2`), with Bitstamp servers hosted in AWS Frankfurt (`eu-central-1`).
4. **Known Exchange Incidents:** Three historical incidents are documented:
   - 2019-07-26 (15 min K8s node failure).
   - 2020-10-20 (52 min WebSocket disconnect due to currency pair subscription limits).
   - 2023-02-03 (12 hours Cloudflare account suspension impacting initial order book snapshots).
5. **Licensing & Access Constraints:** 
   - Historical CSV files for the first day of each month are available as free public samples.
   - Continuous, bulk historical daily archives require a paid data API key.
   - Pricing tiers: Academic (~$650), Solo Quant (~$1,200), Commercial / Prop (~$2,200 – $6,000+).
   - In strict compliance with BTCognitive Prime Directives, no paid credentials or unauthorized purchases were made.

---

## 2. Tardis.dev Bitstamp BTCUSD Technical Specifications

| Parameter | Tardis.dev Specification | BTCognitive Research Requirement | Compliance Status |
| :--- | :--- | :--- | :--- |
| **Exchange Identifier** | `bitstamp` | Bitstamp Spot BTC/USD | **MATCH** |
| **Symbol Identifier** | `BTCUSD` | BTC/USD | **MATCH** |
| **Market Type** | Spot (`spot`) | Spot | **MATCH** |
| **Earliest Available Date** | `2019-03-30T00:00:00.000Z` | $\ge 4$ years continuous history | **EXCEEDS** (7.5 years) |
| **Data Channels** | `trades`, `quotes`, `incremental_book_L2`, `book_snapshot_5`, `book_snapshot_25` | `trades` for OHLCV aggregation | **EXCEEDS** |
| **Timestamp Precision** | Microsecond integer (`timestamp` & `local_timestamp`) | $\le 1$ second resolution | **EXCEEDS** |
| **Trade ID** | Provided where available from Bitstamp WebSocket | Trade deduplication | **MATCH** |
| **Compression Format** | Daily `.csv.gz` archives | Immutable source storage | **MATCH** |

---

## 3. Four-Year Historical Acquisition Plan

### A. Data Volume & Transfer Estimates
Bitstamp BTC/USD is a high-liquidity but moderately trade-dense spot market compared to high-frequency perpetual exchanges.

- **Estimated Daily Trade Count:** ~15,000 to ~40,000 trades per day.
- **Daily Compressed Size (`.csv.gz`):** ~300 KB to ~800 KB per daily trade file.
- **Daily Uncompressed CSV Size:** ~1.5 MB to ~4.0 MB per day.
- **4-Year Scope (1,460 calendar days):**
  - **Total Compressed Download Transfer:** **~0.5 GB to 1.2 GB** (mean estimate: **~730 MB**).
  - **Total Uncompressed Tick Storage:** **~3.5 GB to 5.0 GB**.
  - **Final Aggregated Hourly Parquet Dataset:** **~15 MB**.

### B. Acquisition Protocol & Ingestion Pipeline
1. **Authorization Gate:** Secure user authorization for a Solo/Academic data key.
2. **Batch Downloader Script:** Python-based asynchronous downloader (`scripts/data/download_tardis_bitstamp.py`) utilizing HTTP Range headers, exponential backoff, and SHA-256 integrity validation.
3. **Local Raw Archive Storage:**
   ```
   data/raw/tardis/bitstamp/BTCUSD/
       ├── 2020/
       │   ├── bitstamp_trades_2020-01-01_BTCUSD.csv.gz
       │   └── ...
       ├── manifests/
       │   └── tardis_download_manifest_sha256.json
   ```
4. **Integrity & Checksum Validation:** Every downloaded `.csv.gz` file is validated against Tardis ETag/MD5 and logged into an append-only JSONL provenance ledger.

---

## 4. Alternative Historical Providers Evaluated

| Vendor | History Depth | Spot BTC/USD | Trade Tick Data | Licensing / Accessibility | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tardis.dev** | 2019–present | Yes (`BTCUSD`) | Yes (Microsecond) | Subscription (~$1,200) | **PRIMARY CANDIDATE** |
| **Kaiko** | 2014–present | Yes | Yes (Tick / L2) | Institutional ($5k+) | Cost-prohibitive |
| **CoinAPI** | 2016–present | Yes | Yes (Tick / Agg) | Monthly Quota ($799+) | Complex credit system |
| **Coinbase / Binance** | N/A | Cross-exchange | N/A | Exchange mismatch | Violates single-exchange mandate |

---

## 5. Governed Recommendation & Acceptance Status

1. **Governed Decision:** `CONTINUOUS_DATA_NOT_AVAILABLE` in the existing local repository.
2. **Provider Qualification:** Tardis.dev is formally qualified as the optimal source for Bitstamp historical trade archives.
3. **Next Step:** Await explicit user authorization before acquiring paid subscription credentials.

