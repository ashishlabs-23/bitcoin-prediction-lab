# BTCognitive V32.78 — Statistical Validation Protocol

**Document ID:** `BTC-STA-V3278-001`  
**Milestone:** V32.78 — Asymmetric Regime-Conditioned Entry Research  
**Author:** Specialist Workstream 6 (Econometrics & Multiple-Testing Control)  
**Date:** October 30, 2026  
**Status:** COMPLETE / GOVERNED PROTOCOL  
**Governing Standard:** BTCognitive Operating Contract §5 (Research & Governance Guardrails)  

---

## 1. Executive Summary

Specialist Workstream 6 formalizes the econometric protocols, multiple-testing controls, and statistical significance hurdles required to evaluate regime-conditioned entry models in V32.78.

Because data-snooping and selective reporting are the primary failure modes in empirical quantitative finance, this protocol pre-registers all evaluation metrics, sample-partitioning rules, label purging/embargo requirements, and family-wise error rate corrections prior to comparative hypothesis testing.

---

## 2. Core Econometric Methodology

### 2.1 Chronological Purging and Embargoing
To prevent information leakage and serial correlation across multi-day holding periods ($H \in \{24\text{h}, 72\text{h}, 168\text{h}\}$), evaluation blocks must be strictly isolated:
1. **Purging:** Any observation whose forward outcome window overlaps with an active position is excluded. Once a trade is triggered at $t$, no subsequent signal is processed until the trade resolves at $t + \tau$ ($\tau \le H$).
2. **Embargo:** An additional buffer of $h = 24\text{ hours}$ is enforced between trade termination and subsequent signal eligibility:
   $$\text{Next Eligible Entry} \ge t_{\text{exit}} + 24\text{ bars}$$
This prevents autocorrelation in residual variance from contaminating adjacent observations.

### 2.2 Effective Sample Size ($N_{\text{eff}}$)
Due to remaining market clustering across macroeconomic regimes, nominal sample size $N$ overstates statistical degrees of freedom. The effective sample size is computed via:
$$N_{\text{eff}} = \frac{N}{1 + 2 \sum_{k=1}^m \left(1 - \frac{k}{m}\right) \hat{\rho}_k}$$
where $\hat{\rho}_k$ is the empirical autocorrelation of trade outcomes at lag $k$, and $m$ is the Bartlett kernel bandwidth ($m = \lfloor 4(N/100)^{2/9} \rfloor$).

### 2.3 Diebold–Mariano Test with HLN Correction
When comparing candidate regime strategy $A$ against the baseline unconditional strategy $B$, differential loss is defined as:
$$d_t = \mathcal{L}(e_{A, t}) - \mathcal{L}(e_{B, t})$$
The Harvey–Leybourne–Newbold (HLN 1997) finite-sample modified statistic is:
$$\text{DM}^* = \sqrt{\frac{T + 1 - 2h + h(h - 1)/T}{T}} \cdot \left[ \frac{\bar{d}}{\sqrt{\hat{V}(\bar{d})}} \right]$$
where $h$ is the forecast horizon ($h = 72$ for the primary horizon), and $\text{DM}^*$ is compared against Student's $t$ distribution with $T - 1$ degrees of freedom.

### 2.4 Deflated Sharpe Ratio (DSR) & Multiple-Testing Control
With $K = 15$ candidate configurations evaluated in V32.78, the expected maximum Sharpe ratio under the null hypothesis of zero skill ($H_0: \text{SR} = 0$) increases with $\sqrt{2 \ln K}$.
The Deflated Sharpe Ratio (Bailey & López de Prado, 2014) is computed as:
$$\text{DSR} \equiv \Phi\left( \frac{(\widehat{\text{SR}} - \text{SR}^*) \sqrt{N - 1}}{\sqrt{1 - \hat{\gamma}_3 \widehat{\text{SR}} + \frac{\hat{\gamma}_4 - 1}{4}\widehat{\text{SR}}^2}} \right)$$
where:
$$\text{SR}^* = \sqrt{\frac{V[\{\widehat{\text{SR}}_k\}]}{1}} \cdot \left( (1 - \gamma) \Phi^{-1}\left(1 - \frac{1}{K}\right) + \gamma \Phi^{-1}\left(1 - \frac{1}{K e}\right) \right)$$
$\hat{\gamma}_3$ is skewness, $\hat{\gamma}_4$ is kurtosis, and $\gamma \approx 0.5772$ (Euler–Mascheroni constant). A candidate is rejected unless $\text{DSR} \ge 0.95$ ($p < 0.05$).

---

## 3. Pre-Registered Experiment Matrix ($K = 15$)

| ID | Model / Candidate Code | Direction | Horizon ($H$) | $k_{\text{TP}}$ | $k_{\text{SL}}$ | Primary Condition |
|:---:|:---|:---:|:---:|:---:|:---:|:---|
| 0 | `UNCOND_72H_LONG` (Baseline) | LONG | 72h | 3.0% | 1.50% | Unconditional uniform sampling |
| 1 | `UNCOND_72H_SHORT` (Baseline) | SHORT | 72h | 3.0% | 1.50% | Unconditional uniform sampling |
| 2 | `COMP_BO_72H_LONG` | LONG | 72h | 3.0% | 1.50% | $\mathcal{R}_{\text{comp}}$ + 20-bar Donchian High |
| 3 | `COMP_BO_72H_SHORT` | SHORT | 72h | 3.0% | 1.50% | $\mathcal{R}_{\text{comp}}$ + 20-bar Donchian Low |
| 4 | `TREND_PB_72H_LONG` | LONG | 72h | 3.0% | 1.50% | $\text{TAS} \ge +0.50\%$ + RSI $\in [40, 50]$ |
| 5 | `TREND_PB_72H_SHORT` | SHORT | 72h | 3.0% | 1.50% | $\text{TAS} \le -0.50\%$ + RSI $\in [50, 60]$ |
| 6 | `EXHAUST_72H_LONG` | LONG | 72h | 3.0% | 1.50% | 50-bar Low + Lower Wick $\ge 40\%$ |
| 7 | `EXHAUST_72H_SHORT` | SHORT | 72h | 3.0% | 1.50% | 50-bar High + Upper Wick $\ge 40\%$ |
| 8 | `TREND_PB_NO_HVOL_72H_LONG` | LONG | 72h | 3.0% | 1.50% | Trend Pullback + High-Vol Abstain |
| 9 | `TREND_PB_NO_HVOL_72H_SHORT` | SHORT | 72h | 3.0% | 1.50% | Trend Pullback + High-Vol Abstain |
| 10 | `COMP_BO_24H_LONG` (Sensitivity) | LONG | 24h | 1.5% | 0.75% | Compression Breakout (24h) |
| 11 | `COMP_BO_24H_SHORT` (Sensitivity) | SHORT | 24h | 1.5% | 0.75% | Compression Breakout (24h) |
| 12 | `TREND_PB_24H_SHORT` (Sensitivity) | SHORT | 24h | 1.5% | 0.75% | Trend Pullback (24h) |
| 13 | `TREND_PB_168H_SHORT` (Sensitivity) | SHORT | 168h | 5.0% | 2.50% | Trend Pullback (168h) |
| 14 | `COMP_BO_168H_SHORT` (Sensitivity) | SHORT | 168h | 5.0% | 2.50% | Compression Breakout (168h) |

---

## 4. Minimum Statistical Hurdles for Milestone Advancement

To warrant recommendation for milestone advancement to V32.79, a candidate must satisfy **ALL** of the following criteria:

1. **Sample Size Hurdle:** Clean non-overlapping sample size $N \ge 100$ trades in the out-of-sample window.
2. **Economic Viability:** Net expected return $\mathbb{E}[R_{\text{net}}] > 0$ after deducting retail taker fees (Coinbase Advanced: 87 bps round-trip).
3. **Statistical Significance:** One-tailed $t$-statistic versus fee threshold exceeding critical value ($t > 1.96$, $p < 0.05$) with Deflated Sharpe Ratio $\text{DSR} \ge 0.95$ across the 15 tested variants.
4. **Temporal Stability:** Net expected return must remain strictly positive in both halves of the chronological out-of-sample split (H1 and H2). Any strategy displaying negative net EV in either sub-period is disqualified.

