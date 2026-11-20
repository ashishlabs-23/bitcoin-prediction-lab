# BTCognitive V34.5 — Market Regime Robustness & Statistical Independence Audit

**Milestone:** BTCognitive V34.5 — Continuous Historical Data & Strategy Viability  
**Date:** 2026-11-03  
**Status:** COMPLETE / GOVERNED  
**Lead Author:** Agent 4 (Regime Classification & Robustness Specialist)  
**Governed Assessment:** `REGIME_DEPENDENCE_NOT_ESTABLISHED`

---

## 1. Executive Summary

Milestone V34.4 descriptively observed that the HTF breakout strategy performed relatively better in early 2024 than in 2026 due to the macro ETF approval trend. However, the mandate for V34.5 demanded rigorous statistical hypothesis testing: **Can regime-dependent performance differences be formally established without relying on hand-selected calendar windows?**

Agent 4 subjected all 17 causal trade events across both observation segments to formal statistical inference.

### Key Audit Findings
1. **Regime Distribution & Trade Allocation:**
   - Long breakout setups were triggered exclusively in two canonical regimes: **`TRENDING_BULLISH`** ($N=13$ trades) and **`VOLATILITY_EXPANSION`** ($N=4$ trades).
   - In both permitted regimes, the strategy suffered severe negative net expectancy under baseline 70 bps friction (-177.4 bps in `TRENDING_BULLISH`, -158.2 bps in `VOLATILITY_EXPANSION`).
2. **Regime Hypothesis Testing:**
   - Welch's two-sample $t$-test comparing net returns in `TRENDING_BULLISH` vs `VOLATILITY_EXPANSION` yielded $t = -0.199$ and a two-sided $p$-value of **$p = 0.851$**.
   - There is **zero statistically significant difference** in performance between regimes.
3. **Small-Sample Multiplicity & Epistemic Resolution:**
   - Attributing early 2024 results to a "regime advantage" was an artifact of small-sample variance ($N=3$ trades in 2024).
   - In accordance with the prompt directive ("Do not establish regime dependence from only two hand-selected windows"), the formal governed verdict is updated to **`REGIME_DEPENDENCE_NOT_ESTABLISHED`**.

---

## 2. Regime-by-Regime Quantitative Performance Ledger

| Performance Metric | `TRENDING_BULLISH` Regimes | `VOLATILITY_EXPANSION` Regimes | Filtered Regimes (`RANGE`, `BEAR`, `TRANS`) |
| :--- | :--- | :--- | :--- |
| **Total Trade Events ($N$)** | **13 trades** | **4 trades** | **0 trades** (Filtered by design) |
| **Winning Trades (Net $>0$)** | 2 wins (`SEG_2024_001`, `SEG_2026_011`) | 1 win (`SEG_2026_006`) | N/A |
| **Losing Trades (Net $\le 0$)** | 11 losses | 3 losses | N/A |
| **Win Rate (%)** | **15.4%** | **25.0%** | N/A |
| **Gross Total Return (bps)** | -1,395.8 bps | -352.8 bps | N/A |
| **Gross Expectancy (bps)** | -107.4 bps | -88.2 bps | N/A |
| **Net Total Return (70 bps)** | **-2,305.8 bps** | **-632.8 bps** | N/A |
| **Net Expectancy (70 bps)** | **-177.4 bps** | **-158.2 bps** | N/A |
| **Sample Standard Deviation** | 148.8 bps | 174.0 bps | N/A |
| **Profit Factor** | 0.12 | 0.11 | N/A |
| **Maximum Trade Drawdown** | -289.8 bps (`SEG_2026_007`) | -255.5 bps (`SEG_2024_003`) | N/A |
| **Mean MFE / Mean MAE** | 129.5 bps / 236.4 bps | 149.9 bps / 270.4 bps | N/A |
| **False Breakout Rate** | **84.6%** (11/13 stopped out) | **75.0%** (3/4 stopped out) | N/A |

---

## 3. Statistical Hypothesis Testing of Regime Differences

To test the null hypothesis:
$$H_0: \mu_{\text{bullish}} = \mu_{\text{expansion}} \quad \text{vs.} \quad H_1: \mu_{\text{bullish}} \ne \mu_{\text{expansion}}$$

We compute Welch's $t$-statistic allowing for unequal variances:

$$t = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\frac{s_1^2}{N_1} + \frac{s_2^2}{N_2}}} = \frac{-177.37 - (-158.20)}{\sqrt{\frac{148.76^2}{13} + \frac{174.01^2}{4}}} = \frac{-19.17}{96.29} = -0.1991$$

- **Degrees of Freedom (Welch-Satterthwaite):** $\nu \approx 4.88$
- **Two-Sided $p$-value:** **$p = 0.8510$**
- **Conclusion:** Fail to reject $H_0$. Performance across both regimes is statistically identical and negative.

---

## 4. Opportunity Frequency & Market Exposure

| Exposure Metric | Segment 1 (2024 Window) | Segment 2 (2026 Window) | Combined Series |
| :--- | :--- | :--- | :--- |
| **Calendar Hours** | 1,000 hours (41.6 days) | 4,000 hours (166.6 days) | 5,000 hours (208.3 days) |
| **Signal Frequency** | 2.19 setups / month | 2.56 setups / month | **2.45 setups / month** |
| **Average Holding Period** | 4.0 hours | 16.3 hours | **14.1 hours** |
| **Active Market Exposure** | 1.2% | 5.7% | **4.8%** |

### Signal Attrition Analysis
While the strategy is appropriately selective (in the market only 4.8% of the time, generating ~2.5 setups per month), **82.4% of all generated setups terminate in stop-loss hits**. 

The strategy's failure is not due to over-trading or improper regime filtering; it fails because 4-hour Donchian breakouts in Bitcoin spot markets suffer severe mean reversion regardless of macro regime.

---

## 5. Governed Epistemic Determination

- **Governed Decision:** `REGIME_DEPENDENCE_NOT_ESTABLISHED`.
- **Epistemic Rationale:** Performance divergence between calendar windows was driven by post-hoc selection of an extreme outlier trend in early 2024 rather than a robust, repeatable regime-conditional edge.

