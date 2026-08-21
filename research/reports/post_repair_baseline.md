# 📊 Post-Repair Production Baseline & Hawkes Revalidation Report

**Execution Timestamp:** 2026-08-21T13:13:41.759584+00:00  
**Evidence Boundary:** `2026-08-21T12:15:00Z`  
**Longitudinal State:** `PAUSED_INTEGRITY_REPAIR`  

## 1. Production Model Rebaseline Lock

| Metric | Post-Repair Value | Pre-Repair Historical | Delta vs Ridge Baseline | Status |
| :--- | :--- | :--- | :--- | :--- |
| MFE Error (P50) | Awaiting new closed 24h cycles | 0.3980% | -0.0140% | `REBASELINE_LOCKED` |
| MAE Error (P50) | Awaiting new closed 24h cycles | 0.5620% | -0.0210% | `REBASELINE_LOCKED` |
| P90 MFE Coverage | Awaiting new closed 24h cycles | 93.50% | +3.10% | `REBASELINE_LOCKED` |
| P90 MAE Coverage | Awaiting new closed 24h cycles | 96.80% | +4.20% | `REBASELINE_LOCKED` |
| Joint Path Containment | Awaiting new closed 24h cycles | 91.10% | +2.43% | `REBASELINE_LOCKED` |
| Mean Interval Width | Awaiting new closed 24h cycles | 5.28% | -0.18% | `REBASELINE_LOCKED` |
| Winkler Score (P90) | Awaiting new closed 24h cycles | 6.1420 | -0.4120 | `REBASELINE_LOCKED` |


## 2. Hawkes Shadow Microstructure Revalidation

| Parameter | Value | Provenance Note |
| :--- | :--- | :--- |
| Total Shadow Forecasts | 247 | Consolidated full shadow ledger (migrated from secondary DB) |
| Resolved 5m Outcomes | 21 | Verified closed 5m outcome horizons |
| Empirical P90 Coverage | 100.00% | Nominal target 88.67% satisfied |
| Mean MFE Error | 21.5137% | Microstructure excursion accuracy |
| Mean MAE Error | 20.0139% | Adverse excursion accuracy |
| Mean Winkler Score | 6098.6195 | Conformal interval penalty |
| N_eff | 21 | Effective independent shadow sample size |
| Production Promotion Status | BLOCKED (Shadow Model Only) | Hawkes remains non-executing challenger |


## 3. Provenance & Sample Size Discrepancy Note

- **Historical Note:** The preliminary exploratory shadow session referenced a transient `135` snapshot.  
- **Canonical Reconciliation:** The authoritative migration consolidated the complete historical shadow ledger (`247` forecasts and `21` closed outcomes) into canonical WAL storage with complete primary key integrity.  
- **Governance Lock:** Hawkes remains strictly `VALIDATED_SHADOW_ONLY`. No promotion to production.  
