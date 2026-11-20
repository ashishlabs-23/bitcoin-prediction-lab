# Data Provenance and Market-Data Rights Review (V32.57)

**Audit Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Status:** **BLOCKED — COINBASE MARKET DATA RIGHTS UNRESOLVED**

---

## 1. Executive Licensing Verdict

A public user-facing launch using Coinbase market data is **BLOCKED**.

### Primary Legal & Terms Analysis
Coinbase's official **Market Data Terms of Use** (last updated 7 August 2026, accessible at [coinbase.com/legal/market_data](https://www.coinbase.com/legal/market_data)) explicitly govern all access to Coinbase market data (spot candles, tickers, order books, and trades). Key legal boundaries include:
1. **Personal & Internal Research Default:** The default license grants access solely for internal personal or internal non-commercial research use.
2. **Strict Third-Party Redistribution Ban:** Without prior express written consent from Coinbase Inc., licensees **may not display, redistribute, disseminate, sublicense, or publish** raw Market Data or **Derived Works** to third parties or via public websites.
3. **AI/ML Restriction:** The terms explicitly prohibit utilizing Market Data or Derived Works for **AI/ML model training, development, validation, parameter tuning, or benchmarking** without explicit written authorization.
4. **No Implied Display Rights:** Availability of a public REST/WebSocket endpoint (`api.exchange.coinbase.com`) does **not** grant or imply intellectual property or commercial redistribution rights.

### Product Impact on BTCognitive
BTCognitive is designed as an online public charting and market research intelligence product (similar in category to TradingView). Operating as a public web application displaying real-time or historical Coinbase candles, derived technical indicators, and AI volatility/excursion forecasts directly triggers the prohibition against public display of Derived Works and AI/ML benchmarking.

**Required Action:**
- Obtain prior express written commercial/display licensing from Coinbase via formal enterprise agreement; OR
- Select and integrate an alternative institutional market-data provider with explicit commercial redistribution and public display rights (e.g., Kaiko, CCXT Pro Institutional, Twelve Data Commercial API, or Coin Metrics).
- Until written licensing is executed and in repository custody, public release is **BLOCKED**.

---

## 2. V32.55 Data Condition & Integrity Audit

The canonical historical dataset and research artifacts remain strictly preserved and protected.

### Current Historical File State (V2 vs V3)
- **Dataset Rows:** Exactly **42,237 hourly rows** covering the historical observation window.
- **Missing Candle Intervals:** Exactly **13 absent hourly intervals** distributed across 3 distinct outage windows (not 13 individual null values).
- **Governance Classification:** `ACQUIRED_WITH_REVIEW_REQUIRED`.
- **Zero Synthetic Fabrication Policy:** In accordance with BTCognitive Epistemic Principles (Section 2, AGENTS.md), missing intervals must **never** be silently filled with interpolated, smoothed, or synthetic bars. Gaps remain explicit missing intervals.
- **56-Candle Retrospective Replay Overlap:** An independent verification verified 56 hourly candles matching Coinbase timestamp and OHLCV records. However, this overlap check is strictly interval-scoped; it does **not** validate the remaining 42,181 rows, nor does it resolve the 13 historical gaps, nor does it confer commercial redistribution rights.
- **V3 Reconstruction:** V3 remains an independent, immutable artifact requiring verifiable raw response manifests, hash chains, and gap reconciliations before any status transition can occur.

---

## 3. Protected Artifact Cryptographic Invariants

All six canonical and prospective data artifacts are protected with immutable hash locks and write-block guards:

| Artifact Path | SHA-256 Checksum | Invariant Status |
| :--- | :--- | :--- |
| `data/raw/ohlcv.parquet` | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` | LOCKED / UNMODIFIED |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | LOCKED / UNMODIFIED |
| `data/raw/ohlcv_backfilled.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | LOCKED / UNMODIFIED |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | LOCKED / UNMODIFIED |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | LOCKED / UNMODIFIED |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | LOCKED / UNMODIFIED |

**Verification Evidence:** Hashes re-computed independently on 29 October 2026 match previous records bit-for-bit.

---

## 4. Governed Release Status
- **Public Market Data Serving:** `BLOCKED` (Data Rights Gate P0)
- **Research Experiment:** `INCONCLUSIVE`
- **Prospective Evidence:** `COLLECTING` (0/100 non-overlapping blocks for 168h; 3/100 blocks for 24h)
- **Model Serving Authorization:** `OFFLINE_RESEARCH_ONLY`
- **Live Trading:** `DISABLED`

