# BTCognitive V32.63 — Dataset Integrity & Reconciliation Report

**Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Audit Directory:** `research/reports/v32_63_feature_value_audit/20261029_223400_audit/`  
**Execution Context:** Internal Offline Research Mode (`127.0.0.1:8000`), Python 3.13.14 on Windows 11  

---

## 1. Executive Summary & Resolution of the 42,233 vs. 42,237 Row Count Paradox

Prior audit documents (V32.55 through V32.62) exhibited an apparent contradiction regarding the primary dataset row count:
- Some sections cited **42,237 bars with 13 missing historical candles**.
- Other test suites and manifests recorded **42,233 bars with zero gaps** in `data/raw/ohlcv.parquet`.

An empirical byte-level and timestamp-level reconciliation conducted during this audit reveals the exact mathematical cause of this discrepancy:

| Dataset Identifier | File Path | Row Count | Start Timestamp (UTC) | End Timestamp (UTC) | Missing Candle Gaps | SHA-256 Checksum |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Canonical Runtime Dataset** | `data/raw/ohlcv.parquet` | **42,233** | `2022-01-01 00:00:00+00:00` | `2026-10-26 16:00:00+00:00` | **0 gaps** (Strict 1-hour delta throughout) | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` |
| **Research Replay Dataset (V2)** | `data/research/coinbase_btc_usd_hourly_verified_v2/coinbase_btc_usd_hourly.parquet` | **42,237** | `2022-01-01 00:00:00+00:00` | `2026-10-27 09:00:00+00:00` | **3 gaps (13 missing candles)** | `050ee38e07be06bf95df876bb0e0600f6c27be5188f6fa9b47e5b15be6227db4` |
| **Research Replay Dataset (V3)** | `data/research/coinbase_btc_usd_hourly_verified_v3/coinbase_btc_usd_hourly.parquet` | **42,237** | `2022-01-01 00:00:00+00:00` | `2026-10-27 09:00:00+00:00` | **3 gaps (13 missing candles)** | `050ee38e07be06bf95df876bb0e0600f6c27be5188f6fa9b47e5b15be6227db4` |

### The Exact Mathematical Reconciliation:
$$\text{Rows}(V2/V3) = \text{Rows}(\text{Canonical Raw}) - 0 + 17 \text{ trailing bars} - 13 \text{ missing gap bars}$$
$$42,237 = 42,233 + 17 - 13 = 42,237$$

1. **The 13 Missing Candles in V2/V3:**
   - **Gap 1 (3 bars):** `2023-03-04 17:00 UTC` to `2023-03-04 21:00 UTC` (missing 18:00, 19:00, 20:00).
   - **Gap 2 (5 bars):** `2025-10-25 15:00 UTC` to `2025-10-25 21:00 UTC` (missing 16:00, 17:00, 18:00, 19:00, 20:00).
   - **Gap 3 (5 bars):** `2026-05-08 01:00 UTC` to `2026-05-08 07:00 UTC` (missing 02:00, 03:00, 04:00, 05:00, 06:00).
2. **The 17 Trailing Candles in V2/V3:**
   - `data/research/..._v2` extends through `2026-10-27 09:00:00 UTC`.
   - `data/raw/ohlcv.parquet` terminates at `2026-10-26 16:00:00 UTC`.
   - There are exactly **17 hourly candles** between `2026-10-26 17:00` and `2026-10-27 09:00`.
3. **The Raw Dataset Backfill:**
   - In `data/raw/ohlcv.parquet`, the 13 historical gap candles were backfilled from exchange archive records, but the file was frozen at `2026-10-26 16:00 UTC`.
   - Both datasets are valid within their respective domains. `data/raw/ohlcv.parquet` is the immutable primary source powering the FastAPI backend `/api/candle/` endpoints.

---

## 2. Temporal Boundaries vs. Real-World Audit Date

- **Primary Dataset Range:** `2022-01-01 00:00:00 UTC` to `2026-10-26 16:00:00 UTC` (3.82 years / 1,760 days).
- **Audit Date:** `29 October 2026, 22:34 UTC+05:30` (approx `17:04 UTC`).
- **Lag:** The canonical historical dataset terminates approximately **73 hours (3.04 days)** prior to the current audit execution.
- **Epistemic Classification:** Under BTCognitive Research Principles, all data in `data/raw/ohlcv.parquet` is strictly **retrospective replay data**. It can support historical backtesting, feature warm-up, and UI charting, but CANNOT be represented as a live streaming feed.

---

## 3. Data Cleanness & Boundary Verification

A full pandas validation script inspected all 42,233 rows of `data/raw/ohlcv.parquet`:

| Metric / Check | Value / Result | Contract Invariant | Status |
| :--- | :--- | :--- | :---: |
| **Total Rows** | 42,233 | Monotonic integer sequence | **PASS** |
| **Total Columns** | 7 (`timestamp`, `open`, `high`, `low`, `close`, `volume`, `available_time`) | Schema conformant | **PASS** |
| **NaN / Null Values** | 0 across all 7 columns | Zero NaN tolerance | **PASS** |
| **Infinite Values** | 0 across all numeric fields | Zero Inf tolerance | **PASS** |
| **High >= Low Invariant** | 100% compliant (`high >= low` for all 42,233 rows) | No inverted bars | **PASS** |
| **High >= Close & Open** | 100% compliant | Bounds encompass body | **PASS** |
| **Low <= Close & Open** | 100% compliant | Bounds encompass body | **PASS** |
| **Volume >= 0.0** | 100% compliant (no negative volume) | Non-negative volume | **PASS** |
| **Timestamp Continuity** | Step is strictly 3,600,000 ms (1 hour) | Zero interior gaps | **PASS** |
| **Synthetic Fabrication** | 0 interpolated or fabricated records detected | No synthetic bars | **PASS** |

---

## 4. Upstream Charting Library Inspection

- **Served in Application (`web/index.html`):** TradingView Lightweight Charts `v4.1.3` (loaded via CDN fallback / local vendor asset).
- **Upstream Official Release (TradingView):** `v5.2.1` (major redesign of series primitive API and plugin architecture).
- **Audit Evaluation:**
  - `v4.1.3` correctly supports candlestick rendering, volume histogram series, price lines, and forecast marker overlays.
  - Upgrading to `v5.2.1` introduces breaking changes to `createCandlestickSeries` options and custom marker renderers without adding direct user value for offline research.
  - **Verdict:** Retain `v4.1.3` for current offline research mode. Document upgrade to `v5.2.1` as a deferred non-MVP maintenance task.

