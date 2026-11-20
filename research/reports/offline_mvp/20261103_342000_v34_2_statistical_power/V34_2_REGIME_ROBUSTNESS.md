# BTCognitive V34.2 — Volatility Regime and Target Robustness

**Document ID:** `V34_2_REGIME_ROBUSTNESS`  
**Mission:** `BTCognitive V34.2`  
**Agent:** `Agent 6 (Market Regime & Causal Robustness Specialist)`  
**Scope:** Model Ranking Stability across Realized Volatility Quartile Regimes  
**Operating Mode:** Strictly Offline Research  

---

## 1. Executive Summary & Methodology

Agent 6 evaluated whether out-of-sample volatility model rankings remain stable across market environments. To prevent lookahead leakage, regime thresholds were established strictly on in-sample training realized variance quartiles:
- **Quiet Regime:** $RV_d < 0.0459$ (Annualized Volatility $< 21.4\%$)
- **Normal Regime:** $0.0459 \le RV_d < 0.0825$ (Annualized Volatility $21.4\% - 28.7\%$)
- **Volatility Expansion Regime:** $0.0825 \le RV_d < 0.1670$ (Annualized Volatility $28.7\% - 40.9\%$)
- **Extreme Regime:** $RV_d \ge 0.1670$ (Annualized Volatility $\ge 40.9\%$)

---

## 2. Regime Performance Breakdown (Out-of-Sample QLIKE)

| Market Regime | Sample Size ($N$) | OLS Standard HAR | OLS HAR-RS-DOW | QLIKE Standard HAR | Best Performing Model | Robustness Assessment |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Quiet** | 253 | 0.3650 | 8,792.54 (Failure) | **0.3388** | **QLIKE Standard HAR** | Highly resilient to noise |
| **Normal** | 239 | **0.4598** | 1.2117 | 0.4806 | **OLS Standard HAR** | Standard HAR balanced |
| **Volatility Expansion** | 428 | 0.2647 | 0.3564 | **0.2415** | **QLIKE Standard HAR** | Superior variance tracking |
| **Extreme** | 259 | 0.6138 | **0.4829** | 0.6366 | **OLS HAR-RS-DOW** | Semivariance helps in crisis |

---

## 3. Key Causal Insights

1. **Failure of OLS HAR-RS-DOW in Quiet Markets:**  
   During quiet periods, unconstrained OLS estimates for signed negative semivariance and day-of-week dummies collapse near zero, yielding catastrophic QLIKE explosion ($8,792.54$).
2. **Dominance of QLIKE Standard HAR:**  
   QLIKE Standard HAR wins in both **Quiet** ($0.3388$) and **Volatility Expansion** ($0.2415$), which constitute $57.8\%$ of all evaluated market regimes.
3. **Extreme Regime Specialization:**  
   Signed semivariance ($RS^-$) provides incremental explanatory value primarily during extreme market dislocations, but fails in quiet and normal regimes when estimated without regularization.

