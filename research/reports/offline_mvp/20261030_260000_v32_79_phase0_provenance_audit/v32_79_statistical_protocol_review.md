# V32.79 Phase 0 — Statistical Protocol Review (Workstream G)
**Milestone:** BTCognitive V32.79 — Phase 0 Baseline & Data Provenance Audit  
**Generated:** 2026-10-30  
**Auditor:** Lead Orchestrator — Workstream G (Econometrics & Statistics)  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Purpose

This report documents the statistical protocol requirements for any V32.79 Phase 1 empirical research that the Manager may subsequently approve. It establishes acceptance criteria, sample-size constraints, multiple-comparison corrections, and the exploratory vs. confirmatory evidence separation policy.

---

## 2. Candidate Configuration Count (Multiple Comparison Burden)

The Manager proposed four experimental hypotheses for V32.79. Within each, the following configuration dimensions create a multiple-comparison burden:

### 2.1 $H_{\text{Funding}}$ — Funding Dislocation

| Dimension | Candidate Values | Count |
|---|---|---|
| Funding quantile threshold | e.g., 75th, 80th, 85th, 90th, 95th percentile | 5 |
| Quantile lookback window | e.g., 30d, 90d, 180d | 3 |
| Direction (long/short/both) | Long only, Short only, Both | 3 |
| Horizon | 24h, 72h, 168h | 3 |
| **Total configurations** | 5 × 3 × 3 × 3 = **135** | |

### 2.2 $H_{\text{ETF}}$ — ETF Flow (BLOCKED)

N/A — blocked by provenance. Zero configurations testable.

### 2.3 $H_{\text{Macro}}$ — Fed Regime Conditioning

| Dimension | Candidate Values | Count |
|---|---|---|
| Regime (date-range) | R2, R3, R4, All | 4 |
| Feature threshold | Vol ratio, RSI, momentum | 3 |
| Horizon | 24h, 72h | 2 |
| **Total configurations** | 4 × 3 × 2 = **24** | |

### 2.4 $H_{\text{Macro\_Abstain}}$ — FOMC Abstention (BLOCKED)

N/A — blocked by provenance. Zero configurations testable.

**Total testable configurations across approved hypotheses: ≤ 159**

Under Bonferroni correction at $\alpha = 0.05$: **adjusted significance threshold = 0.05 / 159 ≈ 0.000314**

Under Benjamini-Hochberg FDR control at $q = 0.10$: **applied per ranked p-value sequence**

> [!WARNING]
> With 159 configurations, the probability of finding at least one nominally significant result by chance at $\alpha = 0.05$ is approximately $1 - (1 - 0.05)^{159} \approx 99.97\%$. **Every empirical result in V32.79 must report corrected p-values and must distinguish between the pre-registered primary test and post-hoc exploratory findings.**

---

## 3. OOS Window Status

### 3.1 V32.74–V32.78 OOS Window

| Property | Value |
|---|---|
| Bars used | 31,632 → 42,153 (10,521 hourly bars) |
| Corresponding dates | Approximately Jan 2024 → Oct 2026 |
| Use in prior milestones | V32.74, V32.75, V32.76, V32.77, V32.78 |
| Status | **EXPLORATORY ONLY — cannot be treated as a fresh confirmatory holdout** |

The Manager has explicitly stated: *"The V32.74–78 OOS window has already been examined. It CANNOT be treated as a fresh confirmatory holdout."*

**Any V32.79 work on this window is exploratory only, regardless of sample size.**

### 3.2 Prospective Holdout Status

| Property | Value |
|---|---|
| Clean non-overlapping blocks accumulated | 7 of 100 required |
| Last runner activity | 2026-10-23 13:13:46 UTC |
| Status | FROZEN — DO NOT RESTART |
| Minimum required for confirmatory gate | 100 clean non-overlapping blocks |

**Prospective evidence remains at 7/100 blocks. No confirmatory validation is possible.**

---

## 4. Serial Dependence and Effective Sample Size

### 4.1 Autocorrelation in 24h Returns

Hourly returns over a 24-hour horizon exhibit substantial serial dependence. For a rolling window of $h = 24$ hours:

$$\text{Effective N} \approx \frac{T}{h} = \frac{T}{24}$$

For the 10,521-bar OOS window: $N_{\text{eff}} \approx 10,521 / 24 = 438$ non-overlapping observations.

**This is the maximum effective sample size for 24-hour evaluations. For 72h outcomes:**

$$N_{\text{eff,72h}} \approx 10,521 / 72 = 146$$

**For 168h outcomes:**

$$N_{\text{eff,168h}} \approx 10,521 / 168 = 62$$

At $N_{\text{eff}} = 62$ for 168h outcomes, minimum detectable effect sizes are very large (MDE $> 0.3\sigma$ at 80% power with $\alpha = 0.05$). The 168h horizon is statistically underpowered for any realistic expected effect size.

### 4.2 Newey-West Corrected Standard Errors

Standard t-tests and DM tests assume i.i.d. errors. For overlapping evaluation windows (24h outcomes computed on hourly data), overlapping errors are NOT i.i.d.

**Required correction:** Newey-West HAC standard errors with bandwidth $b = \lfloor 1.3 \cdot h \rfloor$ where $h$ is the outcome horizon in bars.

For 24h horizon: $b = \lfloor 1.3 \times 24 \rfloor = 31$ lags.
For 72h horizon: $b = \lfloor 1.3 \times 72 \rfloor = 93$ lags.

**Alternatively:** Non-overlapping block evaluation (compute outcomes only on bars separated by $\geq h$) avoids the overlap problem at the cost of sample size.

### 4.3 Diebold-Mariano with Harvey-Leybourne-Newbold Correction

All pairwise model comparisons must use the HLN-corrected DM statistic:

$$\text{DM}_{\text{HLN}} = \frac{\bar{d}}{\sqrt{\hat{V}(\bar{d})}} \cdot \sqrt{\frac{T + 1 - 2h + T^{-1}h(h-1)}{T}}$$

where $\bar{d}$ is the mean loss differential and $\hat{V}(\bar{d})$ is the HAC variance estimate.

Reference distribution: **Student's $t_{T-1}$**, not standard normal.

A standard DM test without HLN correction will systematically over-reject the null of equal predictive ability in finite samples — a known bias at small $T$.

---

## 5. DSR (Deflated Sharpe Ratio) Protocol

The DSR corrects the reported Sharpe Ratio for selection bias introduced by testing multiple configurations:

$$\text{DSR}(\hat{SR}) = \Phi\left[\frac{(\hat{SR} - E_K[\max SR_k]) \sqrt{T-1}}{\sigma_{SR}\sqrt{1 - \gamma \hat{SR}^2 + \frac{\hat{SR}^2}{2}(1 + \gamma^2)}}\right]$$

where $\Phi$ is the standard normal CDF, $E_K[\max SR_k]$ is the expected maximum SR across $K$ strategies by chance, $\gamma$ is the skewness/excess kurtosis adjustment term.

**Important:** DSR corrects for selection bias but does NOT replace a net-return test. A strategy may have a positive DSR (positive SR after correction for data-snooping) yet still be unprofitable after realistic trading costs. Both tests are required.

**Protocol:**
1. Compute net-return series after fees, spread, and slippage for each configuration.
2. Compute Sharpe Ratio on the net-return series.
3. Apply DSR correction for $K$ = number of configurations tested.
4. Report both the raw SR and the DSR.
5. Only configurations with DSR > 0 merit further investigation.

---

## 6. Exploratory vs. Confirmatory Evidence Policy

| Category | Window | Interpretation | Promotion Eligibility |
|---|---|---|---|
| **Exploratory** | V32.74–V32.78 OOS window (bars 31,632–42,153) | Hypothesis generation, effect estimation | None — cannot be used for production authorization |
| **Prospective** | Future bars (accumulating post-freeze) | Clean, unseen, non-overlapping blocks | Requires 100 non-overlapping clean blocks |
| **Confirmatory** | Prospective only, after pre-registration | Model authorization decisions | Minimum 100 blocks, pre-registered protocol |

**Current prospective count: 7/100 blocks. Status: NOT_STARTED for confirmatory gate.**

The exploratory OOS window has been examined by 5 research milestones (V32.74–V32.78). Any result from this window carries the full multiple-comparison burden of all prior milestones combined.

---

## 7. Recommended Pre-Registration Template for V32.79 Phase 1

Before any empirical experiment, the following must be documented:

```
1. Primary hypothesis (one only): [H_Funding / H_Macro]
2. Primary test statistic: [net_pnl_bps / sharpe / TP_rate]
3. Primary configuration: [specific quantile, direction, horizon]
4. Pre-specified barrier: [3% TP / 1.5% SL] or [other — must justify]
5. Cost scenario: [24 bps Binance (primary), 87 bps Coinbase (conservative)]
6. Evaluation window: [bars X to Y — explicitly not a fresh holdout]
7. Significance threshold (Bonferroni-corrected): [0.05 / K]
8. DM-HLN correction: YES
9. Newey-West bandwidth: [floor(1.3 × h)]
10. DSR correction: YES
11. Prospective holdout: [NOT STARTED — 7/100 blocks]
```

---

*No external data fetched. No datasets modified. No models trained.*

