# BTCognitive V33.3 — Data Lineage & Provenance Integrity Audit

**Version:** 33.3.0  
**Date:** 2026-10-31  
**Operating Contract:** OFFLINE_RESEARCH_ONLY  
**Lead Orchestrator:** Antigravity  
**Repository Working Tree:** `BTCognitive/` on branch `main`  

---

## 1. Provenance Integrity Mandate

A central principle of BTCognitive governance is **Epistemic Integrity**:
- Distinguish authentic empirical market observations from synthetic heuristics or fabricated figures.
- Isolate quarantined datasets with unresolved source conflicts.
- Ensure all strategy evaluations use strictly point-in-time, causal data.

This audit examines the exact data lineage, file hashes, and evidence validity for every strategy and heuristic evaluated in V33.3.

---

## 2. Classification of Data Feeds & Evidence Sources

We classify all data sources into three categories:
1. **Category A: Authenticated Empirical Data (Governed & Verified)**
2. **Category B: Synthetic Heuristics & Unverified Formulas (Non-Empirical)**
3. **Category C: Quarantined Datasets (Blocked from Production / Closed Research)**

---

## 3. Detailed Data Source Inspection

### Category A: Authenticated Empirical Datasets

| Dataset Path | Row Count | SHA256 Hash | Lineage & Timeframe | Used By | Provenance Status |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **`data/raw/ohlcv.parquet`**<br>(`ohlcv_version_42326_bars.parquet`) | 42,326 | `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057` | Hourly BTC-USD from Coinbase Exchange (Jan 2020 – Oct 2026). Gap-checked; zero lookahead. | `HTF_RANGE_EXPANSION_BREAKOUT`, `MTF_MOMENTUM_TREND`, `VOL_COMPRESSION`, HAR-RS-DOW, Decoupled Analysis. | **EMPIRICALLY_APPROVED** |
| **`data/raw/ohlcv_checkpoint_42233_bars.parquet`** | 42,233 | `f5c15cb11b9d51cf0077c8f8052086382deb1d8577749cbab8d0134842c7a94f` | Verified historical freeze checkpoint through October 17, 2026. | V13 Strategy Tournament Replay, C2 calibration development cohort. | **EMPIRICALLY_APPROVED** |
| **`data/prospective_forecast_ledger.jsonl`** | 7 blocks | `ee58b37c71c5c3ff322af3084d27b306eb0a445a8bd6e01a74b76d8168ccd491` | Untouched prospective out-of-sample forward evaluation blocks. Accumulation paused at 7/100 hurdle. | Prospective evidence monitoring. | **FROZEN — 7/100 — COLLECTOR_INACTIVE** |

*Verification:* The performance figures for `HTF_RANGE_EXPANSION_BREAKOUT` (+11.0 bps institutional, N=194) were generated **strictly from Category A empirical data** (`data/raw/ohlcv.parquet`) aggregated into 4-hour candles without lookahead.

---

### Category B: Synthetic Heuristics & Non-Empirical Formulas

| Subsystem Component | Claimed Metric | Source of Value | Provenance Investigation Finding | Governance Determination |
| :--- | :--- | :--- | :--- | :--- |
| **MEIE Archetypes** (`engine/strategy_selection.py`) | "+32.2 bps Expected Value" | Linear scaling function: `15.0 * score` | **Non-Empirical Heuristic:** Source code inspection reveals that the EV is not calculated from historical trade returns. It is an ad-hoc linear transformation of normalized indicator scores (OFI, Hawkes, VPIN). | **SYNTHETIC_HEURISTIC — CANNOT BE USED AS PERFORMANCE EVIDENCE** |
| **Registry 7/10 Screens** (`engine/regime_strategy_tournament.py`) | "7/10 (70%) and 8/10 (80%) Win Rate" | Static 10-attempt list in `VersionedStrategyRegistry` | **Static Test Fixture:** The lists `recent_tsmom` and `recent_atr_breakout` are hardcoded test fixtures created to verify screening logic, NOT a streaming execution ledger. | **STATIC_REGRESSION_FIXTURE — NOT CONTINUOUS LIVE EVIDENCE** |

---

### Category C: Quarantined Datasets

| Dataset Path | Row Count | SHA256 Hash | Issue / Reason for Quarantine | Governance Status |
| :--- | :---: | :--- | :--- | :--- |
| **`data/raw/binance_funding_2022_2026.parquet`** | 5,113 | `e90282de4f78ebde4b0e253cd71e50233d965062defa9f1b81be5b87da094436` | Unresolved data lineage conflict against `funding.parquet` identified in V32.80B audit. Disagreement in 2025–2026 distribution. | **QUARANTINED_UNRESOLVED (Research Frozen)** |
| **`data/raw/funding.parquet`** | 375 | `f176186ec28c78feac7091fa8dcf1f202145ff3a2ea373426ca3a29ca27dfa66` | Truncated historical sample; lineage conflict. | **QUARANTINED_UNRESOLVED (Research Frozen)** |
| **`data/processed/multi_regime_features.parquet`** | 42,233 | `e37fcc1a896e5a8a60db337f8e49253eaf1d8d011c430e32a23a43d7de04205f` | Synthetic feature columns detected during V32.71 audit. | **QUARANTINED_SYNTHETIC** |
| **`CHRONOS2_FOUNDATION`** | N/A | Amazon Chronos-2 weights | Underperformed simple random-walk persistence benchmark under V32.37 bake-off. | **QUARANTINED_MODEL** |

---

## 4. Integrity Conclusion for V33.3

1. **Clean Separation Established:** Only the Strategy Tournament results from `data/raw/ohlcv.parquet` represent authentic, reproducible empirical trading data.
2. **MEIE Claims Discounted:** The MEIE +32.2 bps claim is formally struck from empirical evaluation as a heuristic artifact.
3. **Quarantine Preserved:** All funding datasets and Chronos2 models remain strictly quarantined with zero influence on trade candidate evaluation.
4. **Validated Base for Optimization:** `HTF_RANGE_EXPANSION_BREAKOUT` is 100% grounded in authentic Coinbase OHLCV data, making it a legitimate candidate for optimization.

