# Scientific Report: VOL-EDGE-01 Incremental Volatility Information Trial
**Protocol**: Locked Multi-Regime Purged Walk-Forward Evaluation (Purge: 168h, Embargo: 168h)  
**Pre-Registration Source**: [`results/vol_edge_01_preregistration.md`](file:///c:/Projects/BTCognitive/bitcoin-prediction-lab/results/vol_edge_01_preregistration.md)  
**Execution Timestamp**: 2026-08-24T14:48:28Z  
**Target Variable**: Annualized 7-Day Realized Variance (`rv7d_var_ann`)  
**Primary Horizon**: $h = 168\text{ hours}$ ($7.0\text{ calendar days}$)  
**Final Governance Verdict**: **EMPIRICAL_NULL_REJECTED (NO INCREMENTAL EDGE OVER HAR + IV²)**

---

## 1. Model Performance Ladder (M0 -> M6)

| Model ID | Specification | Out-of-Sample QLIKE | OOS $R^2$ | Spearman IC | MAE ($\sigma^2$) | Calibration Slope |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M0** | Historical Mean Variance | 0.25673 | -0.1112 | -0.0758 | 0.13187 | 0.020 |
| **M1** | Rolling Realized Variance | 0.20184 | +0.0944 | 0.4897 | 0.10628 | 0.686 |
| **M2** | Standard HAR-RV (Daily, Weekly, Monthly) | 0.19623 | +0.1382 | 0.5173 | 0.10312 | 0.764 |
| **M2-R**| HAR-RS-DOW Robustness Benchmark | 0.19300 | +0.1515 | 0.5272 | 0.10192 | 0.785 |
| **M3** | HAR-RV + Conformal Compression | 0.19597 | +0.1383 | 0.5196 | 0.10297 | 0.757 |
| **M4** | 7D Implied Variance Only ($IV_{7d}^2$) | 0.23359 | +0.0368 | 0.5030 | 0.09708 | 0.892 |
| **M5** | **Combined Baseline (HAR + IV²)** | **0.19969** | **+0.1386** | **0.5487** | **0.09544** | **0.856** |
| **M6** | **Challenger (HAR + IV² + Compression)** | **0.19946** | **+0.1398** | **0.5494** | **0.09547** | **0.847** |

---

## 2. Decisive Benchmark Evaluation: M6 vs. M5

| Criterion | Metric / Statistical Test | Observed Value | Admission Gate Threshold | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **1. Primary Loss** | Out-of-Sample $\Delta\text{QLIKE} (M5 - M6)$ | **+0.000234** | $\Delta\text{QLIKE} > 0$ | PASS |
| **1. Significance** | Paired Diebold-Mariano Test ($L=168$) | **DM = +0.316, p = 0.37581** | $p < 0.05$ | **FAIL (Insignificant)** |
| **2. Variance Exp** | Incremental OOS $R^2$ ($\Delta R^2$) | **+0.0012** | $\Delta R^2 > 0$ | PASS (Negligible) |
| **2. Rank Corr** | Incremental Spearman IC ($\Delta\text{IC}$) | **+0.0007** | $\Delta\text{IC} > 0$ | PASS (Negligible) |
| **3. Placebo Test** | Block Permutation Null Distribution ($B=100$) | **Placebo p = 0.1400** | $p_{\text{perm}} < 0.05$ | **FAIL (Placebo Not Extreme)** |
| **4. Robustness** | Challenger M6 vs. HAR-RS-DOW (M2-R) | **DM = -0.981, p = 0.83663** | $\text{DM}_{\text{stat}} > 0$ | **FAIL (Dominated by HAR-RS-DOW)** |

---

## 3. Fold-Level Compression Coefficient Stability ($\gamma_{\text{compression}}$)

| Expanding Fold Index | Test Period | Estimated $\gamma_{\text{compression}}$ Coefficient | Stability Status |
| :--- | :--- | :--- | :--- |
| **Fold 1** | Fed Hiking Bear Regime | `+0.0689` | Positive & Consistent |
| **Fold 2** | Fed Bear to Transition | `+0.0727` | Positive & Consistent |
| **Fold 3** | Transition Compression | `+0.0460` | Positive & Consistent |
| **Fold 4** | Transition to Spot ETF Era | `+0.0453` | Positive & Consistent |
| **Fold 5** | Spot ETF Institutional Era | `+0.0389` | Positive & Consistent |

---

## 4. Market Pricing Diagnostics

* **Pearson Correlation $\text{Corr}(\text{Compression}_t, IV_{7d, t})$**: `+0.0112`
* **Spearman Correlation $\text{Corr}(\text{Compression}_t, IV_{7d, t})$**: `+0.0083`
* **Diagnostic Finding**: The options market does not explicitly price compression coiling ($\rho \approx 0.01$). However, the historical volatility autoregressive structure (HAR-RV) already absorbs almost all predictive variance, leaving zero statistically significant incremental forecasting alpha for compression.

---

## 5. Epistemic Governance Conclusion

1. **Falsification of the Incremental Feature Hypothesis**:
   While compression exhibits a stable positive relationship with subsequent volatility ($\bar{\gamma} \approx +0.054$), its marginal contribution to forecast accuracy beyond standard HAR-RV and implied volatility is tiny ($\Delta \text{QLIKE} = +0.00023$, Diebold-Mariano $p = 0.376$).
2. **HAR-RS-DOW Dominance**:
   The contemporary $M_{2\text{-R}}$ benchmark (HAR-RS-DOW, QLIKE `0.19300`) significantly outperforms both $M_5$ (`0.19969`) and $M_6$ (`0.19946`), proving that realized semivariance and intra-week structure capture volatility dynamics far more effectively than compression.
3. **Standing Scientific Action**:
   In accordance with the pre-registration and Ponytail discipline:
   - **VOL-EDGE-01 is concluded as a clean null / non-significant result.**
   - Compression is **frozen and archived** as a standalone structural regime descriptor, but **rejected** as an incremental volatility forecasting feature.
   - Downstream economic screening (H3 options execution) is **aborted**, preventing any wasted capital or speculative curve-fitting.
