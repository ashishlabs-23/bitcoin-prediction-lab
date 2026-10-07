# Dataset & Sample-Size Feasibility Audit (Phase 6B2)

**Track ID:** `BTC-ENTRY-TP-SL-V3`  
**Dataset:** `data/raw/btcusd_1-min_data.csv` (Bitstamp BTC/USD Spot, Kaggle v745)  
**Dataset SHA-256:** `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`  
**Audit Date:** `2026-10-07`  
**Resolver Version:** `ENTRY_TP_SL_RESOLVER_V1`  

---

## 1. Raw Dataset Integrity & Continuity Audit

| Metric | Measured Value | Requirement / Benchmark | Status |
|---|---|---|---|
| **Total Rows** | `7,766,111` | $\ge 5,000,000$ 1-minute bars | **`PASS`** |
| **Byte Size** | `393,952,273` bytes | Exact byte match | **`PASS`** |
| **Start Timestamp** | `1325376060` (2012-01-01 00:01:00 UTC) | Historical depth $\ge 10$ years | **`PASS` (14.76 years)** |
| **End Timestamp** | `1791342660` (2026-10-07 03:11:00 UTC) | Recent snapshot coverage | **`PASS`** |
| **Timestamp Continuity** | `7,766,110` consecutive 60-second steps (100.00%) | Monotonic increasing, 0 duplicates | **`PASS`** |
| **Gap Count (> 60s)** | `0` gap events | Contiguous series | **`PASS`** |
| **Null Values** | `0` nulls across all columns | Clean numerical data | **`PASS`** |
| **Price Sanity Checks** | $H \ge L, H \ge O, H \ge C, L \le O, L \le C, P > 0$ | Zero geometric anomalies | **`PASS`** |

---

## 2. Decision Cadence & Forward Path Coverage

- **Total 15-Minute Decision Grid Points ($t_0$):** `517,740` intervals
- **Valid 15-Minute Decision Bars with Causal $\text{ATR}_{14} > 0$:** `510,989` intervals
- **Forward Path Coverage ($H = 240\text{ minutes}$ / 240 bars):**
  - Eligible decision points with 100% complete 240m forward path: `510,973` intervals (99.997%)
  - Decision windows lost to path insufficiency: `16` (only the final 4 hours at the very end of the 14.7-year file).

---

## 3. Sample-Size Feasibility & Capacity Analysis

> **IMPORTANT DISTINCTION:**  
> The numbers below represent **FEASIBILITY UPPER BOUNDS** under theoretical maximum signal triggering. They are **NOT** the actual independent trade count, which will be strictly determined by the selective entry model and market regime filters in Phase 7.

| Scenario / Constraint | Calculation Basis | Theoretical Opportunity Upper Bound |
|---|---|---|
| **Raw 15-Minute Decision Opportunities** | Every 15-minute grid close with valid $\text{ATR}_{14}$ | `510,989` opportunities |
| **Complete 240m Forward Path Opportunities** | Grid points with full forward 240-bar path | `510,973` opportunities |
| **Theoretical Upper Bound (Max Hold = 240m)** | Worst-case: all trades held for full 4-hour horizon under **ONE OPEN POSITION** constraint | **`31,935` independent non-overlapping trades** |
| **Theoretical Upper Bound (Avg Hold = 60m)** | Realistic holding time under barrier touches (~1 hour) under **ONE OPEN POSITION** constraint | **`127,743` independent non-overlapping trades** |
| **Statistical Preregistration Requirement** | Frozen minimum evaluation sample size ($N_{\text{trades}}$) | **`250` independent trades** |
| **Feasibility Safety Multiple** | Upper Bound / Minimum Requirement | **$127.7\times$ to $510.9\times$ Coverage Multiple** |

**Conclusion:** The dataset provides overwhelming sample-size capacity to support the preregistered minimum evaluation sample ($N \ge 250$ independent trades) even after severe selectivity, regime filtering, and temporal purging.

---

## 4. Deterministic Pilot Label Verification (N = 500)

A deterministic pilot slice of 500 decision opportunities across the 14.7-year timeline was evaluated using `TripleBarrierEngine` under `barrier_pair_01` (1.0x TP / 1.0x SL, $H = 240\text{m}$, BASE cost scenario):

- **Total Evaluated:** `500`
- **`TP_FIRST`:** `196` (39.2%)
- **`SL_FIRST`:** `283` (56.6%)
- **`TIMEOUT`:** `21` (4.2%)
- **`DATA_GAP`:** `0` (0.0%)
- **Same-Timestamp Collisions (`same_timestamp_collision=True`):** `3` (0.6%)
  - *All 3 collision events correctly resolved to conservative `SL_FIRST` and preserved `unresolved_intrabar_order=True`.*
- **Mean Net R (Unfiltered Random Direction):** $-0.218R$ (consistent with negative expectancy of random entries under positive trading friction).
