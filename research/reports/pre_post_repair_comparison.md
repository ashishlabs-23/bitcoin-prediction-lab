# 📑 Pre-Repair vs Post-Repair Metric Reconciliation & Comparison Report

**Generated:** 2026-08-21T13:13:41.763554+00:00  
**Status:** `COMPLETED_DATA_INTEGRITY_REPAIR`  

## 1. Architectural & Metric Comparison Table

| Evaluated Metric / Dimension | Pre-Repair Historical Value | Post-Repair Reconciled Baseline | Observed Difference | Root Cause & Semantic Rationale | Comparability Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Directional Win Rate** | 100.0% (Unresolved DEFAULT 1) | Awaiting post-repair resolved cycles (NULL for unresolved) | Elimination of 100% win-rate default bias | Unresolved records previously carried was_correct=1. Now strictly set to NULL. | `NOT DIRECTLY COMPARABLE (Pre-repair metric was methodologically distorted)` |
| **Forecast Evaluation Horizon** | 4 Hours (Label/Resolution Mismatch) | 24 Hours (Contract-Locked) | 20 Hours horizon alignment | Production model trained on 24h targets but resolved on 4h timer. Fixed to 24h. | `NOT DIRECTLY COMPARABLE (Different evaluation horizons)` |
| **On-Chain Metric Semantics** | mvrv_zscore (1.85 fallback) | CoinMetrics CapMVRVFF ratio (explicit DEGRADED states) | Semantic clarification from Z-score to Ratio | Upstream data provides raw market-to-realized ratio; silent 1.85 fallback eliminated. | `VALID (Post-repair preserves actual scientific ratio scale)` |
| **Regime Classification Vocabulary** | 7 V3 Neural Strings / 'NORMAL' bug | 5 CanonicalRegime Enum states | Deterministic normalization to canonical ensemble branches | Prevented unhandled string mismatch in downstream position manager. | `VALID (Preserves intended ensemble routing)` |
| **Database Storage Integrity** | 2 Fragmented DBs (268 orphan shadow rows) | Single Unified SQLite WAL Database | Zero split-brain path risk | Consolidated shadow and production tables into authoritative database. | `VALID (Full ACID and WAL integrity restored)` |
| **Independent Longitudinal Blocks** | 35 Blocks (Historical pre-repair counter) | 0 Blocks (Post-repair baseline reset) | Counter reset to 0 | Pre-repair blocks evaluated under distorted runtime cannot mix with clean post-repair baseline. | `NOT DIRECTLY COMPARABLE (New post-repair evidence sequence begins at 0)` |


## 2. Key Governance Findings

1. **No Performance Degradation:** The underlying forecasting weights (Ridge conformal quantiles and volatility context) remain 100% frozen and unaltered.  
2. **Evidence Reset Rationale:** Historical metrics evaluated under 4h resolution with `was_correct=1` defaults cannot be aggregated with 24h canonical observations without contaminating longitudinal statistics.  
3. **Milestone Restart:** Post-repair longitudinal evidence starts cleanly at block `0`, tracking the new milestone sequence `[0, 5, 10, 20, 30, 40, 60, 90]`.  
