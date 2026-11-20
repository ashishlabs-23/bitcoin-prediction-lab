# BTCognitive V33.2 — Point-in-Time Backtest Results & Comparative Analysis

**Document ID:** `BTC-V33-2-RPT-005`  
**Milestone:** V33.2 (Adaptive Risk Calibration & Volatility-Shift Response)  
**Author:** Lead Quantitative Research Engineer  
**Governing Status:** Verified Empirical Backtest Ledger  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY` | Live Trading `DISABLED`  

---

## 1. Executive Summary & Verification Scope

This report presents the authoritative, strictly causal point-in-time backtest results across all five conformal calibration configurations evaluated in Milestone V33.2.

All candidates were evaluated across exactly the same **5,671 hourly closed candles** from the 2026 chronological holdout (January 1, 2026 00:00 UTC to August 25, 2026 06:00 UTC) with an identical pre-frozen base forecasting model (`HAR-RS-DOW-v1.0`). In accordance with causal execution rules, all forecast updates and scale derivations were restricted strictly to outcomes matured $\ge 168\text{ hours}$ prior to forecast origin.

---

## 2. Master Comparative Results Matrix

| Performance Dimension / Metric | Control: Baseline C2 | Candidate 1: Rolling ($W=720\text{h}$) | Candidate 2: ACI ($\gamma=0.002$) | Candidate 3: FACI (Multi-Expert) | Candidate 4: EnbPI ($W=1440\text{h}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Point-in-Time Coverage** | **$84.89\%$** | $83.23\%$ | $80.44\%$ | $76.18\%$ | **$84.36\%$** |
| **Nominal Target** | $90.00\%$ | $90.00\%$ | $90.00\%$ | $90.00\%$ | $90.00\%$ |
| **Coverage Gap vs. Target** | **$-5.11\text{ pp}$** | $-6.77\text{ pp}$ | $-9.56\text{ pp}$ | $-13.82\text{ pp}$ | **$-5.64\text{ pp}$** |
| **Extreme Volatility Coverage** | **$64.79\%$** | $61.80\%$ | $63.91\%$ | $54.58\%$ | $59.68\%$ |
| **Extreme Sample Count ($N$)** | $568\text{ bars}$ | $568\text{ bars}$ | $568\text{ bars}$ | $568\text{ bars}$ | $568\text{ bars}$ |
| **Extreme 95% Bootstrap CI** | $[60.92\%, 68.84\%]$ | $[57.75\%, 65.85\%]$ | $[59.86\%, 67.78\%]$ | $[50.53\%, 58.63\%]$ | $[55.63\%, 63.73\%]$ |
| **LOW Regime Coverage ($N=1418$)** | $83.00\%$ | $82.37\%$ | $78.70\%$ | $71.44\%$ | **$87.66\%$** |
| **MEDIUM Regime Coverage ($N=2835$)**| **$89.81\%$** | $87.27\%$ | $84.83\%$ | $82.79\%$ | $87.55\%$ |
| **HIGH Regime Coverage ($N=850$)** | $85.06\%$ | **$85.53\%$** | $79.76\%$ | $76.47\%$ | $84.71\%$ |
| **Mean Interval Width** | $0.4389$ | $0.3864$ | $0.4234$ | $0.3790$ | **$0.3606$** |
| **Median Interval Width** | $0.2364$ | $0.2288$ | **$0.2177$** | $0.2217$ | $0.3327$ |
| **Mean Winkler Score ($\alpha=0.10$)**| $1.0444$ | $1.0092$ | $1.0486$ | $1.0326$ | **$0.8740$** |
| **Mean Relative Width Ratio** | $2.71$ | **$2.26$** | $2.55$ | $2.29$ | $2.57$ |
| **Median Relative Width Ratio** | $2.06$ | **$1.82$** | $2.00$ | $1.85$ | $2.44$ |
| **Undercoverage Episodes Count** | $37\text{ episodes}$ | $50\text{ episodes}$ | $53\text{ episodes}$ | $76\text{ episodes}$ | **$18\text{ episodes}$** |
| **Mean Episode Duration** | $23.16\text{ hours}$ | $19.02\text{ hours}$ | $20.92\text{ hours}$ | **$17.78\text{ hours}$** | $49.28\text{ hours}$ |
| **Max Episode Duration** | **$251\text{ hours}$** | $253\text{ hours}$ | $280\text{ hours}$ | **$251\text{ hours}$** | $256\text{ hours}$ |
| **Mean Adaptation Delay** | **$14.49\text{ hours}$** | $14.98\text{ hours}$ | $14.99\text{ hours}$ | $15.96\text{ hours}$ | $17.84\text{ hours}$ |
| **Interval Width Std ($\sigma_w$)** | $0.3615$ | $0.3508$ | $0.3646$ | $0.3427$ | **$0.1629$** |
| **Daily Coverage Std ($\sigma_{\text{daily}}$)**| **$32.58\%$** | $33.68\%$ | $35.35\%$ | $37.44\%$ | $34.09\%$ |
| **Computational Latency** | **$0.0059\text{ ms}$** | **$0.0058\text{ ms}$** | $0.0118\text{ ms}$ | $0.0803\text{ ms}$ | $0.0797\text{ ms}$ |

---

## 3. Key Empirical Findings

1. **Failure of the Adaptive Hypothesis:**
   The primary hypothesis that online adaptive calibration would improve empirical coverage from $84.89\%$ toward $90.0\%$ is **empirically disproven**.
   - Standard ACI degrades coverage to $80.44\%$ ($-4.45\text{ pp}$ worse than C2).
   - Multi-expert FACI degrades coverage to $76.18\%$ ($-8.71\text{ pp}$ worse than C2).
   - Rolling calibration ($W=720\text{h}$) degrades coverage to $83.23\%$ ($-1.66\text{ pp}$ worse than C2).
2. **C2 Retains Top Coverage:**
   The existing baseline C2 remains the top-performing configuration in unconditional coverage ($84.89\%$), extreme-volatility coverage ($64.79\%$), and adaptation delay following expansion shocks ($14.49\text{ hours}$).
3. **EnbPI Tradeoff:**
   EnbPI demonstrates the highest interval sharpness (Winkler $0.8740$) and fewest undercoverage episodes ($18$), but falls short of C2's empirical coverage ($84.36\%$ vs. $84.89\%$) and performs worse in extreme volatility ($59.68\%$ vs. $64.79\%$).
4. **Computational Feasibility:**
   All five candidates execute well within real-time latency budgets ($< 0.1\text{ ms per bar}$). Latency is not a blocker.

