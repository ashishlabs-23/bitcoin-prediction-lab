# V32.79 Phase 0 — Dataset Inventory
**Milestone:** BTCognitive V32.79 — Phase 0 Baseline & Data Provenance Audit  
**Generated:** 2026-10-30  
**Auditor:** Lead Orchestrator (Phase 0 Execution)  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Governance Invariants

- No external API calls made during this audit.
- No protected datasets modified.
- All hashes verified against known-good values from V32.76.
- See `v32_79_protected_hash_verification.json` for full hash registry.

---

## 2. Raw Dataset Inventory

### 2.1 OHLCV Price Datasets

| File | Rows | Columns | Timestamp Range | SHA-256 (first 16) | Status |
|---|---|---|---|---|---|
| `ohlcv_checkpoint_42233_bars.parquet` | 42,233 | 7 | 2022-01-01 → 2026-10-26 16:00 UTC | `f5c15cb11b9d51cf` | ✅ FROZEN CHECKPOINT |
| `ohlcv_version_42326_bars.parquet` | 42,326 | 7 | 2022-01-01 → 2026-10-30 13:00 UTC | `ba06fb533c0b5338` | ✅ POST-INCIDENT VERSION |
| `ohlcv.parquet` (working copy) | 42,326 | 7 | 2022-01-01 → 2026-10-30 13:00 UTC | `ba06fb533c0b5338` | ⚠️ LIVE — identical to post-incident version |
| `ohlcv_pre_backfill_backup.parquet` | 41,434 | 7 | 2022-01-01 → 2026-10-24 08:00 UTC | `c4949e5b5695ffa1` | ✅ PRE-BACKFILL SNAPSHOT |
| `ohlcv_backfilled.parquet` | 42,177 | 7 | 2022-01-01 → 2026-10-24 08:00 UTC | `1e722f33734a89e7` | ℹ️ BACKFILLED VERSION |
| `coinbase_15m.parquet` | 16,200 | 8 | 2026-05-10 → 2026-10-26 17:30 UTC | — | ℹ️ 15-MIN CANDLES (2026 only) |
| `btcusd_1-min_data.csv` | ~7.77M | CSV | Unknown | — | ℹ️ 1-MIN HISTORICAL (unverified range) |

**Columns (ohlcv files):** `timestamp`, `open`, `high`, `low`, `close`, `volume`, `available_time`

**Provenance incident summary:** The 93-bar discrepancy (42,233 → 42,326) results from a test that inadvertently called the live Coinbase Exchange API (mock used `requests.get`; implementation used `urllib.request.urlopen`). V32.76 created the two versioned checkpoints. Both hashes are verified and unchanged.

---

### 2.2 Funding Rate Dataset

| File | Rows | Columns | Timestamp Range | Symbol | Interval |
|---|---|---|---|---|---|
| `binance_funding_2022_2026.parquet` | 5,113 | 5 | 2022-01-01 → 2026-09-01 | `BTCUSDT` (USDⓈ-M perpetual) | 8h (verified) |
| `funding.parquet` | 375 | 3 | 2026-01-01 → 2026-05-05 | BTCUSDT (implied) | 8h |

**Key finding:** All 5,113 rows are `BTCUSDT` (Binance USDⓈ-M perpetual). Zero rows for `BTCUSD_PERP` (COIN-M). The instrument is consistent throughout. Intervals are uniformly 8.000h (±millisecond jitter from `fundingTime` sub-second precision). No genuine non-8h settlements exist. Mark price is 0 for 2,005 rows (all 2022 rows — data quality gap).

---

### 2.3 Microstructure / Features Datasets

| File | Rows | Columns | Timestamp Range | Source Assessment |
|---|---|---|---|---|
| `data/processed/features.parquet` | 2,951 | 26 | 2026-01-03 → 2026-05-05 | Live collected (2026 only). Contains `funding_rate`, `open_interest`, `order_book_imbalance`, `taker_buy_ratio`. |
| `data/raw/oi.parquet` | 3,000 | 3 | 2026-01-01 → 2026-05-05 | Open interest time series (2026 only). |
| `data/raw/onchain.parquet` | 30 | 3 | 2026-10-01 → 2026-10-30 | Synthetic placeholder — 30 rows, uniform timestamps, `mvrv_zscore`, `nupl`. |

---

### 2.4 Processed / Regime Datasets

| File | Rows | Columns | Timestamp Range | Source | Critical Finding |
|---|---|---|---|---|---|
| `data/processed/multi_regime_features.parquet` | 20,978 | 15 | 2022-01-08 → 2024-05-31 | `research/multi_regime_dataset.py` | ⛔ **SYNTHETIC — built from simulated price paths** |

**Critical finding:** See `v32_79_macro_feature_lineage.md` for full analysis. The regime feature file is built from `np.random.normal()` draws seeded with `np.random.seed(42)`. It does not use real OHLCV data.

---

### 2.5 Prospective Ledgers

| File | Lines | Hash (first 16) | Status |
|---|---|---|---|
| `prospective_entry_ledger.jsonl` | 5 | `91c3aed984002f61` | V1 ledger — 5 entries |
| `prospective_entry_ledger_v2.jsonl` | 9 | `e6e33e3c7beb4c25` | V2 ledger — 9 entries (active) |
| `prospective_shadow_v1.jsonl` | 0 | `e3b0c44298fc1c14` | EMPTY (SHA matches empty file) |

Prospective collector (`ShadowFeedRunner-V30.5`, PID 31676) last ran 2026-10-23 13:13:46 UTC. Frozen at **7/100 blocks**. Lock file exists. Do NOT restart.

---

### 2.6 ETF Flow Data

**Result: NO ETF/ETP flow dataset exists locally.**

Search conducted across all 407 data files. Only `data/market_memory.db` matched the keyword "etf" in its filename (it is a SQLite database, not an ETF flow dataset). No CSV, parquet, or JSON files containing ETF, ETP, Farside, iShares, Grayscale, ARK, or 21Shares data were found.

**Determination:** $H_{\text{ETF}}$ is `BLOCKED_BY_PROVENANCE` — no local data, and external acquisition is prohibited under `OFFLINE_RESEARCH_ONLY`.

---

### 2.7 Macro Event Calendar (FOMC/CPI)

**Result: NO macro event calendar exists locally.**

Keyword search for `fomc`, `cpi`, `macro`, `event`, `calendar`, `fed`, `federal`, `reserve` across `data/` yielded only:
- `data/research/l2_stream/l2_burnin_events_*.jsonl` — these are L2 order book burn-in events, not macro calendars.
- `data/research/user_positions/user_position_events.jsonl` — user position events.

No FOMC meeting dates, CPI release timestamps, or macro announcement calendars exist in the repository.

**Determination:** $H_{\text{Macro\_Abstain}}$ requires macro event timestamps with sub-hour release precision. Without a local calendar file with verifiable publication timestamps, this hypothesis is `BLOCKED_BY_PROVENANCE`.

---

## 3. Dataset Coverage Matrix

| Dataset | Coverage Start | Coverage End | Bars (approx.) | Overlap with OHLCV Checkpoint |
|---|---|---|---|---|
| OHLCV Checkpoint (42,233) | 2022-01-01 | 2026-10-26 | 42,233 hourly | — (reference) |
| Binance Funding | 2022-01-01 | 2026-09-01 | 5,113 (8-hourly) | ✅ Full overlap through 2026-09-01 |
| Multi-Regime Features | 2022-01-08 | 2024-05-31 | 20,978 (hourly) | ⛔ SYNTHETIC — not real price data |
| Processed Features | 2026-01-03 | 2026-05-05 | 2,951 (hourly) | Partial (2026 only) |
| Coinbase 15m | 2026-05-10 | 2026-10-26 | 16,200 (15-min) | Partial (2026 only) |
| ETF Flows | — | — | — | MISSING |
| FOMC/CPI Calendar | — | — | — | MISSING |

---

## 4. Data Quality Flags

| Dataset | Flag | Severity | Detail |
|---|---|---|---|
| `binance_funding_2022_2026.parquet` | Mark price = 0 | Medium | 2,005 rows (all 2022) have `mark_price = 0`. Funding rate is populated. |
| `multi_regime_features.parquet` | **Synthetic data** | **Critical** | Built from `np.random.normal()` simulated paths, not real BTCUSD prices. |
| `ohlcv.parquet` | Post-incident version | Medium | Current working copy is the 42,326-bar post-incident file; the pre-incident 42,233-bar checkpoint is preserved. |
| `onchain.parquet` | Synthetic placeholder | High | 30 rows, uniform timestamps — clearly a placeholder dataset. |
| `prospective_shadow_v1.jsonl` | Empty file | Medium | The shadow runner produced 0 entries despite running for some period. |

---

*Report generated as part of V32.79 Phase 0 Baseline & Data Provenance Audit.*  
*No external data fetched. No datasets modified. No models trained.*

