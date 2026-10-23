# BTCognitive V25 — Forecast Validation, Econometric Nesting & Model Comparison Audit

**Specialist Role:** Agent B (Quantitative Forecast Auditor)  
**Date:** 19 October 2026  
**Status:** Verification Complete — Persistence Remains Undefeated  
**Canonical Manifest:** `experiments/results/v25_canonical_forecast_manifest.json`  
**Dataset:** `data/raw/ohlcv.parquet` (41,273 hourly bars, SHA-256 `43c8881b57431759f68fcb7036d78432449d079b11bcaea45f0d0ecfa287e2f6`)  

---

## 1. Executive Summary & Core Results

An independent econometric audit was executed on the canonical walk-forward future-price forecasting tournament across 1h, 4h, and 24h horizons.

### Definitive Metric Matrix:

| Horizon ($h$) | Evaluation Blocks ($N$) | Persistence MAE (USD) | Persistence RMSE (USD) | Ridge L2 MAE (USD) | Ridge L2 RMSE (USD) | Skill Score (%) | DM-HLN Stat ($p$-value) | Clark-West Stat ($p$-value) | Governed Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 Hour** | 15,000 | **$283.66** | **$435.32** | $283.68 | $435.36 | -0.016% | -1.2208 (0.2222) | -0.8238 (0.7950) | `PERSISTENCE_BASELINE_UNBEATEN` |
| **4 Hours** | 3,750 | **$560.48** | **$843.34** | $560.64 | $843.52 | -0.044% | -0.9695 (0.3324) | -0.3969 (0.6543) | `PERSISTENCE_BASELINE_UNBEATEN` |
| **24 Hours** | 625 | **$1,458.31** | **$2,073.67** | $1,458.54 | $2,075.47 | -0.173% | -0.6955 (0.4870) | -0.2928 (0.6151) | `PERSISTENCE_BASELINE_UNBEATEN` |

---

## 2. Source Dataset Provenance & Window Allocation

The primary dataset contains 41,273 continuous hourly closed candles from Coinbase Spot BTC-USD spanning from 2022-01-01 00:00:00 UTC to 2026-10-17 15:00:00 UTC.

### Why Evaluation Origins are Restricted to $[20,000, 35,000]$:
1. **In-Sample Causal Training Window ($[0, 20,000)$):** To prevent lookahead leakage, models are trained strictly on the first 20,000 closed hourly bars (~2.3 years).
2. **Preregistered Walk-Forward Evaluation Window ($[20,000, 35,000]$):** 15,000 out-of-sample hourly bars (~1.7 years) are evaluated using non-overlapping origin steps ($step = h$). This guarantees that each evaluation block is evaluated on data unseen during training.
3. **Retrospective Holdout Buffer ($[35,000, 41,273]$):** The remaining 6,273 bars are preserved as an uninspected historical buffer.
4. **Prospective Ledger ($t > \text{freeze}$):** Live forward observations are logged in `data/prospective_forecast_ledger.jsonl`.

---

## 3. Econometric Audit: Nested Models & Clark-West (2007)

A crucial methodological question addressed in V25 is whether the comparison between Persistence and Ridge L2 represents a **nested** model comparison.

### Mathematical Formulation of Model Nesting:
- **Restricted Model 1 (Persistence Benchmark):**
  $$\hat{y}_{1, t+h|t} = y_t \iff \hat{r}_{1, t+h|t} = 0$$
  Model 1 estimates 0 parameters and asserts that log returns are a martingale difference sequence ($E[r_{t+h}] = 0$).
- **Unrestricted Model 2 (Ridge L2 Challenger):**
  $$\hat{y}_{2, t+h|t} = y_t \cdot \exp(X_t \hat{\beta})$$
  Under the null hypothesis $H_0: \beta = 0$, Model 2 collapses identically to Model 1. **Model 1 is therefore strictly nested within Model 2.**

### Implications of Clark & West (2007):
Clark & West (2007, *Journal of Econometrics*) proved that when Model 1 is nested in Model 2, the sample Mean Squared Prediction Error ($\text{MSPE}_2$) of the unrestricted model is systematically inflated by sample parameter estimation error ($X(X'X)^{-1}X'$ noise).
Under $H_0$, $E[\text{MSPE}_1 - \text{MSPE}_2] < 0$. Therefore, a standard Diebold-Mariano test is undersized and overly conservative.

### Clark-West MSPE Adjustment:
Clark and West propose the adjusted loss differential:
$$\hat{f}_{t+h} = e_{1, t+h}^2 - \left[ e_{2, t+h}^2 - (\hat{y}_{1, t+h} - \hat{y}_{2, t+h})^2 \right]$$
Adding back $(\hat{y}_{1, t+h} - \hat{y}_{2, t+h})^2$ compensates for the estimation noise of the extra parameters. The test is a one-sided $t$-test ($H_0: E[\hat{f}] \le 0$ vs $H_A: E[\hat{f}] > 0$).

### Empirical Findings Under Clark-West:
- **1h Horizon:** $t_{\text{CW}} = \mathbf{-0.8238}$, one-sided $p = \mathbf{0.7950}$
- **4h Horizon:** $t_{\text{CW}} = \mathbf{-0.3969}$, one-sided $p = \mathbf{0.6543}$
- **24h Horizon:** $t_{\text{CW}} = \mathbf{-0.2928}$, one-sided $p = \mathbf{0.6151}$

**Definitive Conclusion:** Even after eliminating the parameter estimation penalty via Clark-West (2007), all test statistics remain strictly negative. There is zero statistically significant evidence that Ridge L2 outperforms persistence. Persistence remains undefeated.
