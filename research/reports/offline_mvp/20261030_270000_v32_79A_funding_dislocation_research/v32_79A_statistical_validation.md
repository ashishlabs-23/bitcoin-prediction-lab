# V32.79A — Statistical Validation (Workstream 5)
**Milestone:** BTCognitive V32.79 Phase 1A — Funding Dislocation Research  
**Generated:** 2026-10-30  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Pre-Registered Protocol

| Requirement | Specified | Applied |
|---|---|---|
| Minimum episodes per arm | 100 | SHORT: 64, LONG: 3 — both FAIL |
| Multiple-testing correction | Bonferroni, K=2, α=0.025 | Applied |
| DM-HLN correction | Student's $t_{T-1}$ | Applied |
| Newey-West bandwidth | 31 lags | Applied |
| Bootstrap CI | 2,000 replications | Applied |
| Chronological stability | First/second half | Applied |

---

## 2. Sample Size Assessment

### 2.1 SHORT Arm (N=64)

At N=64, the minimum detectable effect size for a two-sided test at α=0.025 and power=80% is approximately:

$$\text{MDE} \approx \frac{z_{\alpha/2} + z_\beta}{\sqrt{N}} \cdot \sigma \approx \frac{2.24 + 0.842}{\sqrt{64}} \cdot \hat{\sigma}$$

The sample standard deviation of net P&L per episode (SHORT arm):
- TP episodes: +2.76% each (19 observations)
- SL episodes: −1.74% each (29 observations)  
- EXPIRED episodes: variable (~+0.11% mean, wide spread) (16 observations)

Estimated σ ≈ 2.2% per episode.

$$\text{MDE} \approx \frac{3.08}{\sqrt{64}} \times 2.2\% = \frac{3.08}{8} \times 2.2\% \approx 0.85\%$$

The observed net EV is +0.068%. This is well below the MDE of ~0.85%, meaning that **even if the true net EV were +0.068%, the experiment would have inadequate power to detect it reliably at N=64.**

### 2.2 LONG Arm (N=3)

Statistical inference is impossible at N=3. No power calculation is meaningful.

---

## 3. DM-HLN Test Results

### 3.1 SHORT arm vs. BASELINE_SHORT

$$H_0: E[\text{net EV}^{\text{cond}}] = E[\text{net EV}^{\text{baseline}}]$$

| Statistic | Value |
|---|---|
| Conditioned net EV | +0.068% |
| Baseline net EV | −0.194% |
| Delta | +0.262% |
| DM-HLN statistic | 1.1158 |
| p-value (two-sided, $t_{63}$) | **0.269** |
| Bonferroni threshold | 0.025 |
| Result | **NOT SIGNIFICANT** |

The null hypothesis of equal predictive ability **cannot be rejected**. The observed difference of +0.262pp is consistent with sampling variation at N=64.

### 3.2 LONG arm vs. BASELINE_LONG

Statistical testing is undefined at N=3. The DM statistic is not computable with a meaningful reference distribution.

---

## 4. Bootstrap 95% Confidence Intervals

| Arm | Net EV (Binance) | 95% CI | Zero in CI? |
|---|---|---|---|
| SHORT | +0.068% | [−0.415%, +0.563%] | **YES — CI includes zero** |
| LONG | +1.260% | [−1.740%, +2.760%] | **YES — CI includes zero** |
| BASELINE_LONG | −0.225% | [−0.305%, −0.145%] | No (negative throughout) |
| BASELINE_SHORT | −0.194% | [−0.275%, −0.111%] | No (negative throughout) |

Both conditioned arm CIs include zero, confirming that the observed positive net EVs are consistent with zero economic effect.

---

## 5. Chronological Stability Analysis

### SHORT arm

| Half | Episodes | Net EV (Binance) |
|---|---|---|
| First half (earliest 32 episodes) | 32 | **−0.390%** |
| Second half (latest 32 episodes) | 32 | **+0.526%** |

**Sign reversal detected.** The strategy lost money in the first half and made money in the second half. This is a textbook pattern of temporal instability / regime dependence. The first-half performance (−0.390%) is definitively below breakeven; the second-half performance (+0.526%) barely exceeds breakeven at Binance fees.

Possible explanations (all speculative at N=32 per half):
1. Funding-rate dynamics changed as the BTCUSDT perpetual market matured (more institutional participants, tighter basis, more responsive mean-reversion).
2. Regime-dependent behavior: first half includes the 2022 bear market stress episodes where funding signals were less reliable.
3. Random variation: at N=32 per half, the sign reversal could be pure noise.

**No causal explanation is established. The instability is treated as a negative finding.**

---

## 6. Multiple-Testing Accounting

| Test | K | α | Bonferroni threshold |
|---|---|---|---|
| SHORT vs. baseline | 1 of 2 | 0.05 | 0.025 |
| LONG vs. baseline | 2 of 2 | 0.05 | 0.025 |

With K=2 pre-specified tests, the Bonferroni correction reduces the per-test threshold to 0.025. The SHORT arm p-value of 0.269 does not approach this threshold.

Additionally: the pre-registration committed to one primary configuration (threshold = ±25% ann, horizon = 24h, barrier = 3%/1.5%). No secondary configurations were tested; therefore no within-experiment data-snooping adjustment is required beyond the K=2 arm correction.

---

## 7. Effective Sample Size and Dependence Assessment

### 7.1 Episode independence

The 64 SHORT episodes are non-overlapping by construction (24h cooldown). However, temporal clustering during stress events means episodes may not be independent draws from a stationary distribution.

Augmented Dickey-Fuller informal check: The 64 episode net-P&L values do not exhibit obvious serial autocorrelation (inspecting episode outcomes visually shows no persistent run of TP or SL outcomes). However, formal testing is underpowered at N=64.

### 7.2 Conclusion on dependence

Treating the 64 episodes as approximately independent is a working assumption with acknowledged uncertainty. The effective N is best described as "64 (optimistic)" to "30–40 (conservative, accounting for clustering)." Even the optimistic N=64 is below the pre-specified minimum of 100.

---

## 8. Formal Statistical Determination

| Test | Result |
|---|---|
| Minimum episode requirement (100) | **FAIL — both arms below minimum** |
| DM-HLN significance (SHORT) | **NOT SIGNIFICANT** (p=0.269, threshold=0.025) |
| 95% CI excludes zero (SHORT) | **NO — CI straddles zero** |
| Chronological stability | **FAIL — sign reversal between halves** |
| Effective N adequate for power | **FAIL — MDE exceeds observed effect at N=64** |

**Overall statistical determination: `INSUFFICIENT_EVIDENCE`**

The data provides no statistically reliable evidence that a ±25% annualized BTCUSDT funding threshold predicts BTCUSD price direction or net expected value over 24 hours.

This determination does not rule out the existence of such an effect. It establishes that the present dataset — with only 64 qualifying SHORT episodes and 3 LONG episodes over the 4.67-year overlap period — cannot distinguish a genuine effect from noise at the pre-specified acceptance criteria.

---

*No external data fetched. No datasets modified. No models trained.*

