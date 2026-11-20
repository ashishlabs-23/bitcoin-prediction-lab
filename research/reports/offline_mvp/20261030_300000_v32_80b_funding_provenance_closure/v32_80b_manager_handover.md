# V32.80B — Funding Data Provenance Closure: Manager Handover Report

**Milestone:** BTCognitive V32.80B — Funding Data Provenance Closure  
**Generated:** 2026-10-30T18:25:00Z  
**Lead Orchestrator:** Antigravity  
**Final Governed Milestone Determination:** `SOURCE_LINEAGE_UNRESOLVED`  
**Operating Contract:** `OFFLINE_RESEARCH_ONLY`  

---

## Executive Summary

V32.80B has executed a forensic investigation into the provenance, source lineage, and distribution properties of `data/raw/binance_funding_2022_2026.parquet`, specifically auditing the $+0.000100$ upper boundary observed in 2022, 2025, and 2026.

### Key Forensic Findings:
1. **The Nature of $+0.000100$ Clarified:**
   - $+0.000100$ ($0.01\%$ per 8h) is Binance's **default interest rate component**, which serves as an automatic funding rate clamp when contract premium is mild ($|P - I| \le 0.05\%$).
   - In 2025 and 2026, the series is **not** a frozen constant: it contains $874$ unique values in 2025 and $670$ in 2026, with over $65\%$ of values fluctuating continuously below $0.000100$.
   - However, positive rates in 2022, 2025, and 2026 are **strictly bounded from above by $+0.000100$**, whereas 2023 and 2024 unclamp frequently up to $+0.000881$.
2. **Local Pipeline Cleanliness:**
   - Ingestion code in `research/download_binance_funding_history.py` contains **zero clipping, rounding, or clamping logic**.
   - The `/fapi/v1/fundingRate` API only returns settled funding rates, meaning **no field substitution** (e.g. replacing funding rate with interest rate) occurred.
3. **Internal Conflict with `funding.parquet` Discovered:**
   - A direct comparison against contemporaneous local file `data/raw/funding.parquet` (covering Jan–May 2026) revealed that `funding.parquet` recorded rates up to **$+0.000821$**, with **$113$ settlements exceeding $+0.000228$**.
   - The correlation between the two local files for the exact same 2026 timestamps is **$r = 0.0159$ (virtually zero)**.
   - This proves an **irreconcilable data conflict** between two local datasets purporting to record the same contract.
4. **Governed Determination:**
   - Because external network calls are prohibited under `OFFLINE_RESEARCH_ONLY`, we cannot query live exchange archives to resolve which file represents authentic exchange reality.
   - We formally reject the hypothesis that 2025–2026 was a "natural dormant market regime."
   - The provenance of `data/raw/binance_funding_2022_2026.parquet` is classified as:
     **`SOURCE_LINEAGE_UNRESOLVED`**
   - Strategy status remains **`INSUFFICIENT_EVIDENCE`**. No edge is claimed, and no strategy is promoted.

---

## 1. Resolution of the Five Investigation Areas

### 1. The $+0.000100$ Discontinuity Investigated
- **2022:** 0 observations $> 0.000100$; 337 observations ($30.8\%$) $== 0.000100$; 242 observations $< 0$.
- **2023:** 69 observations $> 0.000100$; 422 observations ($38.5\%$) $== 0.000100$; 111 observations $< 0$.
- **2024:** 213 observations $> 0.000100$; 462 observations ($42.1\%$) $== 0.000100$; 92 observations $< 0$.
- **2025:** 0 observations $> 0.000100$; 188 observations ($17.2\%$) $== 0.000100$; 141 observations $< 0$.
- **2026:** 0 observations $> 0.000100$; 49 observations ($6.7\%$) $== 0.000100$; 208 observations $< 0$.

### 2. Source Lineage Established
- Acquisition script: `research/download_binance_funding_history.py`.
- Endpoint: `https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT`.
- Transformations: None. Raw floats stored directly to parquet.
- Mark price zeros in 2022 and early 2023 reflect Binance's historical API schema prior to adding markPrice to the response payload.

### 3. Settlement Intervals Verified
- Exactly $5,113$ rows across 1,705 days ($99.96\%$ complete).
- All $5,112$ consecutive intervals are **strictly 8.000 hours** ($\pm 31\text{ ms}$ jitter). Zero 4h or 1h intervals.
- The annualization multiplier of $1,095$ ($3 \times 365$) is exact.

### 4. The 2022–2026 Distribution Explained
- The absence of $> 0.000228$ observations post-2024 in this file cannot be accepted as an empirical market regime because contemporaneous local data (`data/raw/funding.parquet`) shows $113$ such spikes during the same period ($r = 0.0159$).
- An upstream endpoint formatting shift, contract difference, or historical aggregation smoothing in the `/fapi/v1/fundingRate` archive is the likely cause, but cannot be verified offline.

### 5. Final Governed Status
- **Milestone Decision:** `SOURCE_LINEAGE_UNRESOLVED`
- **Funding Strategy Research:** Closed under `INSUFFICIENT_EVIDENCE`.
- **Trading / Model Promotion:** `DISABLED` / `OFFLINE_RESEARCH_ONLY`.

---

## 2. Test Suite & Invariants Status

- **Governance & Regression Suite (8 files):** ✅ **57/57 PASS** in 14.39s.
- **Operational Freshness Suite (2 files):** ⚠️ **9 FAIL** retained as operational health alert due to offline candle staleness (>3.8h age vs. 3.0h gate).
- **All Protected Hashes:** Verified and MATCH in `v32_80b_protected_hash_verification.json`.

---

## 3. Deliverables Registry

All 8 deliverables are generated in [`research/reports/offline_mvp/20261030_300000_v32_80b_funding_provenance_closure/`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_300000_v32_80b_funding_provenance_closure/):
1. [`v32_80b_annual_funding_distribution.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_300000_v32_80b_funding_provenance_closure/v32_80b_annual_funding_distribution.md)
2. [`v32_80b_funding_source_lineage.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_300000_v32_80b_funding_provenance_closure/v32_80b_funding_source_lineage.md)
3. [`v32_80b_interest_vs_total_rate_audit.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_300000_v32_80b_funding_provenance_closure/v32_80b_interest_vs_total_rate_audit.md)
4. [`v32_80b_settlement_interval_audit.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_300000_v32_80b_funding_provenance_closure/v32_80b_settlement_interval_audit.md)
5. [`v32_80b_2025_2026_discontinuity_analysis.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_300000_v32_80b_funding_provenance_closure/v32_80b_2025_2026_discontinuity_analysis.md)
6. [`v32_80b_protected_hash_verification.json`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_300000_v32_80b_funding_provenance_closure/v32_80b_protected_hash_verification.json)
7. [`v32_80b_independent_red_team.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_300000_v32_80b_funding_provenance_closure/v32_80b_independent_red_team.md)
8. [`v32_80b_manager_handover.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_300000_v32_80b_funding_provenance_closure/v32_80b_manager_handover.md) (This Report)

