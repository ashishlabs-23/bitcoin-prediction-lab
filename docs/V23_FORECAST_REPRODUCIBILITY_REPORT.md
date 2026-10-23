# BTCognitive V23 — Forecast Reproducibility & Econometric Validation Report

**Version:** 1.0.0  
**Effective Date:** 19 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Data Artifact:** `data/raw/ohlcv.parquet` (SHA-256: `43c8881b57431759f68fcb7036d78432449d079b11bcaea45f0d0ecfa287e2f6`)  
**Canonical Manifest:** `experiments/results/v23_canonical_forecast_manifest.json`  

---

## 1. Executive Summary

The V23 Forecast Reproducibility audit investigates and resolves the discrepancy between previously published forecast accuracy numbers in V18, V19, V20, and V22. By running a first-principles, causal walk-forward tournament across the complete 41,273-row BTCUSD dataset, we establish the authoritative canonical performance metrics.

### Key Takeaway:
The simpler **Persistence / Random Walk Baseline** ($\hat{P}_{t+h} = P_t$) remains unbeaten by the Ridge L2 regularized model across all tested horizons. The difference in error is statistically insignificant ($p > 0.20$), confirming that complex models have not improved on the persistence baseline for unconditional hourly BTCUSD price levels.

---

## 2. Forensic Reconstruction of Historical Discrepancies

| Version | Evaluated Data Scope | 1h Persistence MAE | 4h Persistence MAE | 24h Persistence MAE | Root Cause of Number Difference |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **V18** | 500-origin sample (scaffolding) | $422.39 | $865.35 | $2,322.18 | Small sample during initial prototype construction. |
| **V19** | ~35,000 bars (pre-late-2026 volatility) | $264.99 | $538.10 | $1,312.40 | Truncated dataset ending before the late-2026 volatility expansion. |
| **V20** | Full 41,273 bars (complete historical record) | $283.66 | $560.48 | $1,458.31 | True full-dataset walk-forward evaluation. |
| **V22 UI** | Full dataset backend with legacy UI fallback | $264.99 (UI fallback) | $531.06 (UI fallback) | $1,299.82 (UI fallback) | UI `web/app.js` contained a hardcoded fallback object from V19. |
| **V23 Canonical** | **Full 41,273 bars (Reproduced & Certified)** | **$283.66** | **$560.48** | **$1,458.31** | **Unified canonical manifest; UI dynamically mapped to canonical data.** |

---

## 3. Canonical Forecast Tournament Results

The walk-forward evaluation protocol strictly enforces:
- **Causal point-in-time features:** Zero lookahead ($t_{\text{feature}} \le t_{\text{origin}} < t_{\text{target}}$).
- **Training window:** 20,000 closed hourly candles.
- **Evaluation origins:** Non-overlapping evaluation blocks with step size equal to horizon $h$ (1h: 15,000 blocks; 4h: 3,750 blocks; 24h: 625 blocks).
- **Statistical testing:** Diebold-Mariano (1995) with Harvey-Leybourne-Newbold (1997) finite-sample correction against Student's $t_{T-1}$.

### Performance Summary Table:

| Horizon | Sample Size ($N$) | Persistence MAE (USD) | Persistence RMSE (USD) | Ridge L2 MAE (USD) | Ridge L2 RMSE (USD) | Skill Score (%) | HLN $p$-value | Official Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 Hour** | 15,000 | **$283.66** | $435.32 | **$283.68** | $435.36 | -0.016% | 0.2222 | `PERSISTENCE_BASELINE_UNBEATEN` |
| **4 Hours** | 3,750 | **$560.48** | $843.34 | **$560.64** | $843.52 | -0.044% | 0.3324 | `PERSISTENCE_BASELINE_UNBEATEN` |
| **24 Hours** | 625 | **$1,458.31** | $2,073.67 | **$1,458.54** | $2,075.47 | -0.173% | 0.4870 | `PERSISTENCE_BASELINE_UNBEATEN` |

### Methodological Notes:
1. **Skill Score Definition:** $\text{Skill} = 1.0 - \frac{\text{MSE}_{\text{model}}}{\text{MSE}_{\text{persistence}}}$. Negative skill indicates the model produces larger mean squared error than the random walk baseline.
2. **Diebold-Mariano / HLN Hypothesis:** Null hypothesis $H_0: E[d_t] = 0$ (loss differential between Ridge and Persistence is zero). With $p$-values of $0.2222$, $0.3324$, and $0.4870$, the null hypothesis cannot be rejected at any standard significance level ($\alpha = 0.05$ or $0.10$).
3. **Target Separation:** The price forecast models estimate $P_{t+h}$. They are strictly separated from HAR-RS-DOW, which models 7-day annualized realized variance (`rv7d_var_ann`) and has separate research governance.

---

## 4. UI Alignment & Fix Verification

1. **Elimination of Hardcoded Fallbacks:** Modified `web/app.js` to dynamically load and display the canonical dictionary with exact reproduced values ($283.66, $560.48, $1,458.31).
2. **Mandatory Card Subtitles:**
   - Persistence Card: **"Not a trained AI forecast"** (`BASELINE_ONLY`).
   - Ridge L2 Card: **"Offline research candidate"** (`EXPERIMENTAL_RESEARCH_CANDIDATE`).
   - Empirical Quantiles: **"Not a calibrated prediction interval"** (`HISTORICAL_REFERENCE_ONLY`).
3. **Regression Test:** Automated verification in `tests/test_v23_forecast_reconciliation_and_audit.py` passes with zero errors.
