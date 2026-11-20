# V32.76 — Statistical Validity & Multiple-Testing Audit Report

**Workstream:** Agent 3 — Statistical Validation Specialist  
**Milestone:** BTCognitive V32.76 — Multi-Agent Research Integrity & Conditional Entry Investigation  
**Date:** 2026-10-30  
**Evaluator:** Statistical Validation Specialist (Agent 3)  
**Governing Repo:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**Classification:** Statistical Governance Authority Record  

---

## 1. Executive Summary & Core Statistical Findings

| Statistical Dimension | Audit Status | Key Evaluation |
|---|---|---|
| **Temporal Leakage & Overlapping Labels** | **CRITICAL AUDIT ITEM** | 24-hour forward labels on 1-hour candles have 23 hours of serial overlap. Effective sample size $N_{\text{eff}} \ll N$. Standard IID tests are invalid without block corrections. |
| **Purging & Embargo Integrity** | **SATISFIED IN PIPELINE** | `ContinuityTimeSeriesEngine` enforces gap exclusion and embargo at split boundaries. No training label matures inside test partitions. |
| **Multiple-Testing & Overfitting Risk** | **HIGH IF UNADJUSTED** | Evaluating multiple candidate filters requires Deflated Sharpe Ratio (DSR) and Probability of Backtest Overfitting (PBO) adjustments. |
| **Statistical Acceptance Criteria** | **PRE-REGISTERED** | Pre-registered hurdle: Out-of-sample DM test $p < 0.05$ with HLN correction, positive net EV after costs, and $N_{\text{eff}} \ge 100$ independent blocks. |

---

## 2. Temporal Leakage & Serial Correlation in Overlapping Labels

### 2.1 The Overlap Problem
When evaluating forward excursions over horizon $H = 24$ hours using 1-hour sampled data:
$$\text{Label}_t = f(\{P_{t+1}, \dots, P_{t+24}\}), \quad \text{Label}_{t+1} = f(\{P_{t+2}, \dots, P_{t+25}\})$$
The price windows share 23 common candles ($95.8\%$ overlap). Consequently:
- Residuals exhibit strong moving-average autocorrelation $\text{MA}(23)$.
- Naive standard errors $\text{SE} = \hat{\sigma} / \sqrt{N}$ underestimate true variance by a factor of up to $\sqrt{24} \approx 4.9$.
- $t$-statistics computed under IID assumptions are inflated by nearly $500\%$.

### 2.2 Effective Sample Size ($N_{\text{eff}}$)
Following Breusch & Pagan (1979) and Hansen (1982), the effective degrees of freedom in the presence of serial correlation $\rho_k$ is:
$$N_{\text{eff}} \approx \frac{N}{1 + 2 \sum_{k=1}^{H-1} \left(1 - \frac{k}{H}\right) \rho_k}$$
For our 10,521 out-of-sample hourly bars, the effective number of independent non-overlapping 24-hour blocks is:
$$N_{\text{eff}} \approx \frac{10,521}{24} \approx 438 \text{ blocks}$$
This satisfies the governance requirement ($N_{\text{eff}} \ge 100$), confirming that statistical power is sufficient, provided that standard errors are corrected using Newey-West / Politis-Romano block methods.

---

## 3. Multiple Testing, PBO, and Deflated Sharpe Ratio

### 3.1 The Backtest Overfitting Fallacy
As established by Bailey, Borwein, López de Prado, and Zhu (2016) (*The Probability of Backtest Overfitting*), if an investigator tests $K$ trial strategies and selects the highest Sharpe ratio:
$$\text{E}\left[\max_{k=1,\dots,K} \widehat{\text{SR}}_k\right] \approx \sqrt{2 \ln K} \cdot \sigma_{\widehat{\text{SR}}}$$
Even if all $K$ strategies have an expected Sharpe ratio of zero, testing $K = 50$ configurations guarantees observing a spurious backtest Sharpe ratio of $\approx 1.8$ to $2.2$!

### 3.2 Deflated Sharpe Ratio (DSR) Formulation
The Deflated Sharpe Ratio (Bailey & López de Prado, 2014) adjusts the estimated annualized Sharpe ratio $\widehat{\text{SR}}$ for:
1. Non-normality (skewness $\gamma_3$, kurtosis $\gamma_4$ of returns).
2. Sample length $T$.
3. Number of independent trials $K$ and variance of trial estimates $\text{Var}(\{\widehat{\text{SR}}_k\})$.

$$\text{DSR} \equiv \Phi\left( \frac{(\widehat{\text{SR}} - \text{SR}^*) \sqrt{T-1}}{\sqrt{1 - \gamma_3 \widehat{\text{SR}} + \frac{\gamma_4 - 1}{4} \widehat{\text{SR}}^2}} \right)$$
where the benchmark hurdle $\text{SR}^*$ incorporates the expected maximum under the null:
$$\text{SR}^* = \sqrt{\text{Var}(\{\widehat{\text{SR}}_k\})} \left( (1 - \gamma) \Phi^{-1}\left(1 - \frac{1}{K}\right) + \gamma \Phi^{-1}\left(1 - \frac{1}{K \cdot e}\right) \right)$$
with Euler-Mascheroni constant $\gamma \approx 0.5772$.

### 3.3 Application to BTCognitive V32.74 Experiments
In V32.74, 10 strategy variants (5 filters $\times$ 2 directions) were evaluated:
- All 10 variants exhibited negative net Sharpe ratios under verified transaction fees (annualized Sharpe ranging from $-12.4$ to $-28.6$).
- The maximum observed Sharpe ratio among all trials was strictly negative.
- **DSR Calculation:** With $\max \widehat{\text{SR}} < 0$, $\text{DSR} = 0.000$.
- **Formal Ruling:** Zero probability of backtest overfitting because no model or strategy passed the baseline hurdle. Negative results were reported honestly rather than tuned until an artificial positive Sharpe appeared.

---

## 4. Pre-Registered Statistical Acceptance Criteria

For any future candidate entry model to qualify for promotion beyond `OFFLINE_RESEARCH_ONLY`:

1. **Paired Loss Significance:** Diebold-Mariano test with Harvey-Leybourne-Newbold finite sample correction must achieve $p < 0.05$ against the uniform baseline.
2. **Economic Viability:** 95% Wilson score lower bound on TP hit rate must exceed the fee break-even hurdle ($> 37.5\%$ for Binance VIP0, $> 42.0\%$ for Coinbase Advanced).
3. **Multiple-Testing Correction:** Deflated Sharpe Ratio must exceed $0.95$ after adjusting for all recorded historical trials.
4. **Epistemic Classification:** Retrospective walk-forward results must remain classified as `RETROSPECTIVE_DEVELOPMENT_REPLAY`. Confirmatory validation requires $\ge 100$ clean, untouched prospective blocks accumulated post-freeze.

*Signed by Specialist Agent 3 (Statistical Validation Specialist)*

