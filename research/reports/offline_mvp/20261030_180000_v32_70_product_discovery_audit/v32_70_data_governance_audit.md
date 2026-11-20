# BTCognitive V32.70 — Data Infrastructure & Research Governance Audit

**Audit Date:** 30 October 2026  
**Milestone:** V32.70  
**Target:** Datasets, Data Collectors, Licences, Provenance & Protected Artifact Hashes  

---

## 1. Inventory of Raw & Processed Datasets

All files located in `data/raw/` were audited for file size, row count, column structure, date coverage, and cryptographic hash:

| File Path | Size | Rows | Columns | Date Range | Primary Source / Exchange |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `data/raw/ohlcv.parquet` | **2.28 MB** | 42,233 | 7 | 2022-01-01 00:00 to 2026-10-26 16:00 UTC | Coinbase BTC-USD Spot (Backfilled & Repaired) |
| `data/raw/ohlcv_backfilled.parquet` | **2.27 MB** | 42,177 | 7 | 2022-01-01 00:00 to 2026-10-24 08:00 UTC | Pre-final backfill milestone snapshot |
| `data/raw/ohlcv_pre_backfill_backup.parquet`| **2.23 MB** | 41,434 | 7 | 2022-01-01 00:00 to 2026-10-24 08:00 UTC | Frozen pre-repair reference dataset |
| `data/raw/coinbase_15m.parquet` | **811.5 KB** | 16,200 | 8 | 2026-05-10 23:45 to 2026-10-26 17:30 UTC | Coinbase BTC-USD 15-minute Spot |
| `data/raw/binance_funding_2022_2026.parquet`| **142.4 KB** | 5,113 | 5 | 2022-01-01 00:00 to 2026-09-01 00:00 UTC | Binance BTCUSDT Perpetual Funding Rate |
| `data/raw/funding.parquet` | **12.3 KB** | 375 | 3 | 2026-01-01 00:00 to 2026-05-05 16:00 UTC | Historical sample funding rates |
| `data/raw/oi.parquet` | **79.8 KB** | 3,000 | 3 | 2026-01-01 00:00 to 2026-05-05 23:00 UTC | Open Interest sample records |
| `data/raw/onchain.parquet` | **3.5 KB** | 30 | 3 | 2026-09-27 to 2026-10-26 UTC | Daily MVRV and On-Chain indicators |
| `data/raw/btcusd_1-min_data.csv` | **384.7 MB**| ~4.5M | 8 | Multi-year historical | Kaggle / Coinbase 1-minute historical tick data |

---

## 2. Protected Research Files & Bit-Identical Integrity

Under the BTCognitive operating contract, 6 canonical research artifacts are protected by mandatory pre/post execution SHA-256 hash checks. Any bit modification is a critical governance violation:

| Protected Artifact Path | Canonical SHA-256 Hash | V32.70 Verified Match |
| :--- | :--- | :--- |
| `data/raw/ohlcv.parquet` | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` | **BIT-IDENTICAL (MATCH)** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **BIT-IDENTICAL (MATCH)** |
| `data/raw/ohlcv_backfilled.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **BIT-IDENTICAL (MATCH)** |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **BIT-IDENTICAL (MATCH)** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **BIT-IDENTICAL (MATCH)** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **BIT-IDENTICAL (MATCH)** |

---

## 3. Market-Data Licensing & Permitted Uses Matrix

We evaluated the legal rights and contractual boundaries of available data sources:

| Data Source | Current Access Mode | Public Redistribution | AI Model Training | Derived Indicators | Commercial SaaS Use | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Bitstamp DLA** | Unconfigured (Awaiting DLA) | **PERMITTED** (Under DLA) | **PERMITTED** (Internal) | **PERMITTED** | **PERMITTED** | **Top Priority for Spot Charting** (Execute contract) |
| **CoinGecko Paid API** | Unconfigured (Evaluated) | **PERMITTED** (With attribution) | **FORBIDDEN** (Explicitly barred) | **PERMITTED** | **PERMITTED** (Paid tiers) | **Top Priority for Benchmark Index** |
| **Coinbase Public REST**| Active in Shadow Runner | **UNKNOWN / RESTRICTED** | **UNKNOWN** | **PERMITTED** (Private) | **RESTRICTED** | Retain for private local research only |
| **Binance Vision / ff137**| Downloadable archives | **FORBIDDEN** (CC BY-NC-SA 4.0) | **FORBIDDEN** (Non-commercial) | **RESTRICTED** | **FORBIDDEN** | Disqualified for production product |
| **CCXT Library** | Installed in `requirements.txt`| **NONE** (Library is MIT, 0 data rights) | **NONE** | **NONE** | **NONE** | Client library only; does not license data |

---

## 4. Causal Boundaries & Training/Validation Leakage Controls

1. **Information-Availability Firewall:**
   - Every feature computed in `engine/feature_cache.py` uses strictly historical timestamps: $t_{\text{feature}} \le t_{\text{decision}} < t_{\text{maturity}}$.
   - Open/incomplete hourly bars are explicitly stripped via `is_closed == True`.
2. **Delayed Outcome Resolution:**
   - In `engine/prospective_worker.py` and `engine/shadow_feed_runner.py`, forward forecast outcomes (e.g. 24h or 168h variance) are resolved strictly **after** the forward period has closed.
   - Predictions are committed to append-only JSONL ledgers before forward candles exist.
3. **Purged Cross-Validation with Embargo:**
   - Walk-forward splits in `validation/purged_split.py` enforce a minimum 168-hour embargo buffer between training and test sets to eliminate autoregressive serial dependence leakage.

